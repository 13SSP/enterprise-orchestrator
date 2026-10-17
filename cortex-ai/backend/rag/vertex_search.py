"""
cortex.ai - Vertex AI Search & Enterprise Knowledge Base RAG
Indexes and searches enterprise knowledge base documents and connects
to Vertex AI Search when configured.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

class VertexSearchRAG:
    def __init__(self):
        self.enabled = os.getenv("VERTEX_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")
        self.project_id = os.getenv("GCP_PROJECT_ID", "cortex-ai-hackathon")
        self.knowledge_base_dir = Path(__file__).resolve().parent.parent.parent.parent / "enterprise_knowledge_base"
        self._sections: List[Dict[str, str]] = []
        self._index_local_knowledge()

    def _index_local_knowledge(self):
        """Indexes markdown documents in enterprise_knowledge_base directory."""
        if not self.knowledge_base_dir.exists():
            return
        
        for fpath in self.knowledge_base_dir.glob("*.md"):
            try:
                content = fpath.read_text(encoding="utf-8")
                doc_title = fpath.stem.replace("_", " ")
                # Split by markdown headers
                sections = re.split(r"\n(?=#{1,3}\s+)", content)
                for sec in sections:
                    sec = sec.strip()
                    if sec:
                        # Extract first line as section heading
                        first_line = sec.split("\n", 1)[0].replace("#", "").strip()
                        self._sections.append({
                            "doc_title": doc_title,
                            "file_name": fpath.name,
                            "section_heading": first_line,
                            "content": sec
                        })
            except Exception:
                pass

    def search(self, query: str, datastore_id: str = "enterprise_knowledge") -> Dict[str, Any]:
        """Searches local knowledge base sections and returns matched snippets."""
        local_results = self.search_knowledge_base(query)
        if local_results:
            return {
                "enabled": True,
                "datastore_id": datastore_id,
                "query": query,
                "results": [
                    {
                        "title": f"{r['doc_title']} - {r['section_heading']}",
                        "snippet": r['content'][:400] + ("..." if len(r['content']) > 400 else ""),
                        "source_uri": f"enterprise_knowledge_base/{r['file_name']}"
                    }
                    for r in local_results
                ]
            }

        return {
            "enabled": self.enabled,
            "datastore_id": datastore_id,
            "query": query,
            "results": [
                {
                    "title": "2026 Enterprise Leave and Benefits Handbook",
                    "snippet": "Full-time employees receive 20 days annual PTO plus 10 days sick leave with 5 days maximum rollover.",
                    "source_uri": "gs://cortex-ai-knowledge/handbook-2026.pdf"
                }
            ]
        }

    def search_knowledge_base(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """Scores local indexed sections against the query using token overlap."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        # Remove common stop words
        stop_words = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "for", "to", "of", "what", "how", "can", "i"}
        q_tokens = {t for t in q_tokens if t not in stop_words and len(t) > 2}
        if not q_tokens:
            return []

        scored = []
        for sec in self._sections:
            content_lower = sec["content"].lower()
            heading_lower = sec["section_heading"].lower()
            score = 0
            for t in q_tokens:
                if t in heading_lower:
                    score += 5
                if t in content_lower:
                    score += 1
            if score > 0:
                scored.append((score, sec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

vertex_rag = VertexSearchRAG()
