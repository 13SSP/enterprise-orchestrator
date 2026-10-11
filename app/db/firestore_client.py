import os
import json
import logging
from typing import Dict, Any, List, Optional, Generator
from pathlib import Path

from app.config import settings

logger = logging.getLogger("enterprise.db.firestore")


class DocumentSnapshot:
    """Mirrors Google Cloud Firestore DocumentSnapshot."""
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]], exists: bool = True):
        self.id = doc_id
        self._data = data or {}
        self.exists = exists

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class LocalQuery:
    """Mirrors Firestore Query filters."""
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
    """Mirrors Firestore DocumentReference."""
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
    """Mirrors Firestore CollectionReference."""
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

    def add(self, data: Dict[str, Any], doc_id: Optional[str] = None) -> tuple[Any, LocalDocumentReference]:
        import uuid
        actual_id = doc_id or str(uuid.uuid4())
        ref = self.document(actual_id)
        ref.set(data)
        return None, ref


class FirestoreClientWrapper:
    """
    Unified Google Firebase / Cloud Firestore client wrapper.
    Attempts to initialize Google Cloud Firestore / Firebase.
    If no cloud credentials or project are present, automatically falls back
    to an enterprise local file-persisted Firestore engine.
    """
    def __init__(self):
        self._native_client = None
        self._mode = "LOCAL"
        self._project_id = settings.FIRESTORE_PROJECT_ID or "enterprise-orchestrator-db"
        self._local_storage_dir = Path(settings.DATA_DIR) / "firestore_db"
        self._local_storage_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_client()

    def _initialize_client(self):
        # 1. Check if user configured Google Cloud credentials or Firebase service account
        creds_path = settings.FIREBASE_CREDENTIALS_PATH
        if creds_path and os.path.exists(creds_path):
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore
                if not firebase_admin._apps:
                    cred = credentials.Certificate(creds_path)
                    firebase_admin.initialize_app(cred)
                self._native_client = firestore.client()
                self._mode = "GOOGLE_FIREBASE_LIVE"
                logger.info(f"Connected to Live Google Firebase Firestore using {creds_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize Firebase Admin with credentials {creds_path}: {e}")

        # 2. Check if google-cloud-firestore can connect via ADC or Project ID
        if settings.FIRESTORE_PROJECT_ID and not settings.FIRESTORE_USE_LOCAL_FALLBACK:
            try:
                from google.cloud import firestore
                self._native_client = firestore.Client(project=settings.FIRESTORE_PROJECT_ID)
                self._mode = "GOOGLE_CLOUD_FIRESTORE_LIVE"
                logger.info(f"Connected to Live Google Cloud Firestore for project {settings.FIRESTORE_PROJECT_ID}")
                return
            except Exception as e:
                logger.warning(f"Could not connect to Google Cloud Firestore with project {settings.FIRESTORE_PROJECT_ID}: {e}")

        # 3. Fallback to Local Firestore Engine
        self._mode = "FIRESTORE_EMULATED_STORAGE"
        logger.info(f"Using Firestore Local Storage at {self._local_storage_dir}")

    @property
    def mode(self) -> str:
        return self._mode

    def collection(self, collection_name: str):
        if self._native_client:
            return self._native_client.collection(collection_name)
        return LocalCollectionReference(self._local_storage_dir, collection_name)

    def get_status(self) -> Dict[str, Any]:
        collections = []
        if self._native_client:
            try:
                collections = [c.id for c in self._native_client.collections()]
            except Exception:
                collections = ["live_query_restricted"]
        else:
            if self._local_storage_dir.exists():
                collections = [p.name for p in self._local_storage_dir.iterdir() if p.is_dir()]

        return {
            "mode": self._mode,
            "project_id": self._project_id,
            "storage_path": str(self._local_storage_dir),
            "is_live_google_cloud": self._native_client is not None,
            "collections": collections
        }


# Global singleton instance
firestore_db = FirestoreClientWrapper()
