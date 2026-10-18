"""
cortex.ai - Unified Firestore Client
Supports:
1. Google Cloud Firestore Emulator Suite (FIRESTORE_EMULATOR_HOST=localhost:8080)
2. Live Google Cloud Firestore (GCP Project / ADC)
3. Offline Local JSON Storage engine (zero-dependency fallback)
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator

logger = logging.getLogger("cortex.database.firestore")

class DocumentSnapshot:
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]], exists: bool = True):
        self.id = doc_id
        self._data = data or {}
        self.exists = exists

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class LocalQuery:
    def __init__(self, collection_ref: 'LocalCollectionReference', filters: Optional[List[tuple]] = None, limit_val: Optional[int] = None):
        self.collection_ref = collection_ref
        self.filters = filters or []
        self._limit_val = limit_val

    def where(self, field: str, op: str, value: Any) -> 'LocalQuery':
        new_filters = list(self.filters)
        new_filters.append((field, op, value))
        return LocalQuery(self.collection_ref, new_filters, self._limit_val)

    def limit(self, count: int) -> 'LocalQuery':
        return LocalQuery(self.collection_ref, self.filters, count)

    def stream(self) -> Generator[DocumentSnapshot, None, None]:
        docs = list(self.collection_ref.stream())
        filtered = []
        for doc in docs:
            d = doc.to_dict()
            match = True
            for field, op, val in self.filters:
                doc_val = d.get(field)
                if op in ("==", "eq"):
                    if doc_val != val:
                        match = False
                        break
                elif op == "!=":
                    if doc_val == val:
                        match = False
                        break
                elif op in (">", "gt"):
                    if not (doc_val is not None and doc_val > val):
                        match = False
                        break
                elif op in (">=", "gte"):
                    if not (doc_val is not None and doc_val >= val):
                        match = False
                        break
                elif op in ("<", "lt"):
                    if not (doc_val is not None and doc_val < val):
                        match = False
                        break
                elif op in ("<=", "lte"):
                    if not (doc_val is not None and doc_val <= val):
                        match = False
                        break
                elif op in ("array-contains", "in_array"):
                    if not isinstance(doc_val, list) or val not in doc_val:
                        match = False
                        break
            if match:
                filtered.append(doc)

        if self._limit_val is not None:
            filtered = filtered[:self._limit_val]

        for item in filtered:
            yield item


class LocalDocumentReference:
    def __init__(self, collection_dir: Path, doc_id: str):
        self.collection_dir = collection_dir
        self.id = doc_id
        self.file_path = collection_dir / f"{doc_id}.json"

    def set(self, data: Dict[str, Any], merge: bool = False) -> None:
        self.collection_dir.mkdir(parents=True, exist_ok=True)
        if merge and self.file_path.exists():
            existing = self.get().to_dict()
            existing.update(data)
            data = existing
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def get(self) -> DocumentSnapshot:
        if not self.file_path.exists():
            return DocumentSnapshot(self.id, None, exists=False)
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return DocumentSnapshot(self.id, data, exists=True)
        except Exception as e:
            logger.error(f"Error reading document {self.id}: {e}")
            return DocumentSnapshot(self.id, None, exists=False)

    def update(self, field_updates: Dict[str, Any]) -> None:
        doc = self.get()
        if not doc.exists:
            raise KeyError(f"Document {self.id} does not exist.")
        data = doc.to_dict()
        data.update(field_updates)
        self.set(data)

    def delete(self) -> None:
        if self.file_path.exists():
            self.file_path.unlink()


class LocalCollectionReference:
    def __init__(self, base_dir: Path, collection_name: str):
        self.base_dir = base_dir
        self.id = collection_name
        self.collection_dir = base_dir / collection_name

    def document(self, doc_id: str) -> LocalDocumentReference:
        return LocalDocumentReference(self.collection_dir, doc_id)

    def where(self, field: str, op: str, value: Any) -> LocalQuery:
        return LocalQuery(self).where(field, op, value)

    def limit(self, count: int) -> LocalQuery:
        return LocalQuery(self).limit(count)

    def stream(self) -> Generator[DocumentSnapshot, None, None]:
        if not self.collection_dir.exists():
            return
        for file in self.collection_dir.glob("*.json"):
            doc_id = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                yield DocumentSnapshot(doc_id, data, exists=True)
            except Exception as e:
                logger.error(f"Failed to read file {file}: {e}")


class FirestoreClient:
    def __init__(self):
        self._native_client = None
        self._mode = "LOCAL_STORAGE"
        self._project_id = os.getenv("GCP_PROJECT_ID", os.getenv("FIRESTORE_PROJECT_ID", "cortex-ai-hackathon"))
        self._storage_dir = Path(__file__).resolve().parent / "firestore_storage"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._init_client()

    def _init_client(self):
        # 1. Check if Firebase Emulator host is set
        emulator_host = os.getenv("FIRESTORE_EMULATOR_HOST")
        if emulator_host:
            try:
                from google.cloud import firestore
                self._native_client = firestore.Client(project=self._project_id)
                self._mode = f"FIREBASE_EMULATOR ({emulator_host})"
                logger.info(f"Connected to Firestore Emulator at {emulator_host}")
                return
            except Exception as e:
                logger.warning(f"Could not connect to Firestore emulator: {e}")

        # 2. Check if GCP ADC or Service Account Credentials are configured
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.exists(creds_path):
            try:
                from google.cloud import firestore
                self._native_client = firestore.Client(project=self._project_id)
                self._mode = "GOOGLE_CLOUD_FIRESTORE_LIVE"
                logger.info("Connected to Live Google Cloud Firestore via credentials file")
                return
            except Exception as e:
                logger.warning(f"Failed to connect to Google Cloud Firestore via credentials: {e}")
        elif os.getenv("K_SERVICE") or (os.getenv("GCP_PROJECT_ID") and os.getenv("GCP_PROJECT_ID") != "cortex-ai-demo"):
            try:
                from google.cloud import firestore
                self._native_client = firestore.Client(project=self._project_id)
                self._mode = "GOOGLE_CLOUD_FIRESTORE_LIVE"
                logger.info("Connected to Live Google Cloud Firestore via ADC")
                return
            except Exception as e:
                logger.info(f"Live Firestore not directly reachable via ADC, using local storage: {e}")

        # 3. Fallback to Local Storage Engine
        self._mode = "FIRESTORE_LOCAL_ENGINE"
        logger.info(f"Using Firestore Local Storage engine at {self._storage_dir}")

    @property
    def mode(self) -> str:
        return self._mode

    def collection(self, collection_name: str):
        if self._native_client:
            return self._native_client.collection(collection_name)
        return LocalCollectionReference(self._storage_dir, collection_name)

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self._mode,
            "project_id": self._project_id,
            "storage_path": str(self._storage_dir),
            "is_emulator": "EMULATOR" in self._mode,
            "is_live_gcp": self._mode == "GOOGLE_CLOUD_FIRESTORE_LIVE"
        }


# Global database instance
db = FirestoreClient()
