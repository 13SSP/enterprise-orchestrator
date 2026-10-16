"""
Unit Tests for Define Domain Models & Schemas
"""

import pytest
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from financial_models import FinancialModelsService, FinancialModelsItem


def test_create_item_success():
    svc = FinancialModelsService()
    item = svc.create("test-1", "Sample Entity")
    assert item.id == "test-1"
    assert item.title == "Sample Entity"
    assert item.status == "active"
    assert svc.get("test-1") is not None


def test_create_duplicate_raises_error():
    svc = FinancialModelsService()
    svc.create("test-dup", "Original")
    with pytest.raises(ValueError, match="already exists"):
        svc.create("test-dup", "Duplicate")


def test_empty_id_raises_validation_error():
    svc = FinancialModelsService()
    with pytest.raises(ValueError, match="must not be empty"):
        svc.create("", "Invalid")
