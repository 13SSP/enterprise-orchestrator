"""
Calculators App - Define Domain Models & Schemas
Module: app/schemas/financial_models.py
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class FinancialModelsItem(BaseModel):
    id: str = Field(..., description="Unique entity ID")
    title: str = Field(..., description="Entity name or title")
    status: str = Field("active", description="Entity status")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FinancialModelsService:
    def __init__(self):
        self._storage: Dict[str, FinancialModelsItem] = {}

    def create(self, item_id: str, title: str) -> FinancialModelsItem:
        if not item_id or not title:
            raise ValueError("Item ID and title must not be empty.")
        if item_id in self._storage:
            raise ValueError(f"Item {item_id} already exists.")
        item = FinancialModelsItem(id=item_id, title=title)
        self._storage[item_id] = item
        return item

    def get(self, item_id: str) -> Optional[FinancialModelsItem]:
        return self._storage.get(item_id)

    def list_all(self) -> List[FinancialModelsItem]:
        return list(self._storage.values())
