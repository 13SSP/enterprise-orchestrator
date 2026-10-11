import os
import json
import uuid
import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from app.config import settings
from app.core.observability import observability

class KnowledgeDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    scope: str  # e.g., 'hr_policies', 'it_runbooks', 'finance_guidelines'
    content: str
    source_type: str = "document_ai_ingest"  # or 'manual_upload', 'markdown_runbook'
    author_team: str = "Enterprise Admin"
    tags: List[str] = Field(default_factory=list)

class RAGManager:
    """
    Enterprise RAG Layer modeled on Vertex AI Search datastores.
    Enforces strict team-boundary isolation at the datastore level.
    """
    def __init__(self):
        self.storage_file = os.path.join(settings.DATA_DIR, "knowledge_stores.json")
        self._docs: Dict[str, KnowledgeDocument] = {}
        self._load_or_initialize()

    def _load_or_initialize(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        doc = KnowledgeDocument(**item)
                        self._docs[doc.id] = doc
            except Exception as e:
                print(f"[RAG] Error loading documents: {e}, initializing default stores")
                self._init_default_documents()
        else:
            self._init_default_documents()

    def _save_documents(self):
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump([doc.model_dump() for doc in self._docs.values()], f, indent=2)

    def _init_default_documents(self):
        defaults = [
            KnowledgeDocument(
                title="Employee Paid Time Off (PTO) & Leave Policy 2026",
                scope="hr_policies",
                content="""All full-time employees accrue 20 days of Paid Time Off (PTO) per calendar year, plus 10 company holidays.
Bereavement leave is 5 days of paid time. Unused PTO up to 5 days rolls over into Q1 of the next year.
Requests exceeding 3 consecutive days require manager approval in Workday 2 weeks in advance.
Parental leave: 16 weeks of 100% paid leave for all new parents following birth or adoption.""",
                source_type="document_ai_pdf",
                author_team="Human Resources",
                tags=["hr", "pto", "leave", "benefits"]
            ),
            KnowledgeDocument(
                title="Health, Dental, and Vision Benefits Summary",
                scope="benefits_handbook",
                content="""The company provides comprehensive health coverage through Blue Cross Blue Shield PPO and Kaiser HMO.
Dental insurance covers 100% of preventive care, 80% of basic procedures, and 50% of major services.
Annual wellness stipend: $1,200 per employee for gym memberships, mental wellness apps, or ergonomic office gear.""",
                source_type="document_ai_pdf",
                author_team="Human Resources",
                tags=["benefits", "insurance", "wellness"]
            ),
            KnowledgeDocument(
                title="Cloud Production Incident Runbook (Sev-1 & Sev-2)",
                scope="it_runbooks",
                content="""In the event of an outage or degraded latency > 500ms on core APIs:
1. Declare incident in #incident-war-room on Slack and tag @oncall-ops.
2. Check Grafana dashboards at https://metrics.internal.corp/dashboards/cluster-prod.
3. If bad deployment caused regression, execute rollback via CLI or trigger rollback tool.
4. For deadlocks, initiate rolling restart with health verification.
Post-mortem documentation must be filed in Jira within 48 hours.""",
                source_type="markdown_runbook",
                author_team="IT & Operations",
                tags=["devops", "incident", "kubernetes", "runbook"]
            ),
            KnowledgeDocument(
                title="Corporate Travel and Expense Reimbursement Policy",
                scope="finance_guidelines",
                content="""Meals during business travel are capped at $75 per day (receipts required for expenses above $25).
Flights under 6 hours must be booked in Economy / Main Cabin class.
Hotel accommodation cap is $250/night for tier-1 cities (NYC, SF, London) and $180/night for other locations.
All expense reports must be submitted within 30 days of travel via the Finance Portal.""",
                source_type="document_ai_pdf",
                author_team="Finance",
                tags=["finance", "expenses", "travel", "policy"]
            ),
            KnowledgeDocument(
                title="Zero Trust Security Architecture & Access Standards",
                scope="security_standards",
                content="""All internal services must be protected by Identity-Aware Proxy (IAP) or Google Cloud Identity Platform.
Service-to-service communication requires mutual TLS (mTLS) with short-lived SPIFFE/SPIRE certificates.
Production database access requires ephemeral JIT (Just-In-Time) privilege elevation with multi-party approval.""",
                source_type="markdown_runbook",
                author_team="Security Ops",
                tags=["security", "zero-trust", "iam", "compliance"]
            ),
        ]
        self._docs = {d.id: d for d in defaults}
        self._save_documents()

    def add_document(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        self._docs[doc.id] = doc
        self._save_documents()
        return doc

    def list_documents(self, scope: Optional[str] = None) -> List[KnowledgeDocument]:
        if scope:
            return [d for d in self._docs.values() if d.scope == scope]
        return list(self._docs.values())

    def list_scopes(self) -> List[str]:
        return list(set(d.scope for d in self._docs.values()))

    def search_knowledge(
        self,
        query: str,
        allowed_scopes: List[str],
        top_k: int = 3,
        trace_id: str = "",
        user: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves relevant document chunks strictly confined to the agent's knowledge scopes.
        Simulates Vertex AI Search datastore retrieval.
        """
        if not allowed_scopes:
            return []

        query_tokens = set(re.findall(r"\w+", query.lower()))
        scored_matches = []

        for doc in self._docs.values():
            if doc.scope not in allowed_scopes:
                continue

            # Compute term match overlap score
            doc_text = f"{doc.title} {doc.content} {' '.join(doc.tags)}".lower()
            doc_tokens = set(re.findall(r"\w+", doc_text))
            
            overlap = query_tokens.intersection(doc_tokens)
            if not overlap:
                continue

            score = len(overlap) / (len(query_tokens) + 1.0)
            # Boost if title matches
            for t in overlap:
                if t in doc.title.lower():
                    score += 0.4

            scored_matches.append({
                "doc_id": doc.id,
                "title": doc.title,
                "scope": doc.scope,
                "content": doc.content,
                "source_type": doc.source_type,
                "score": round(score, 3)
            })

        scored_matches.sort(key=lambda x: x["score"], reverse=True)
        top_matches = scored_matches[:top_k]

        observability.log_rag_retrieval(
            trace_id=trace_id,
            user=user or {"sub": "system"},
            query=query,
            scopes=allowed_scopes,
            matches_found=len(top_matches),
            sources=[m["title"] for m in top_matches]
        )

        return top_matches

rag_manager = RAGManager()
