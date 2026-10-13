"""
Unit Tests for Implement Domain Schemas & Models
"""

import pytest
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from models import ModelsService, ModelsItem


def test_create_item_success():
    svc = ModelsService()
    item = svc.create("test-1", "Sample Entity")
    assert item.id == "test-1"
    assert item.title == "Sample Entity"
    assert item.status == "active"
    assert svc.get("test-1") is not None


def test_create_duplicate_raises_error():
    svc = ModelsService()
    svc.create("test-dup", "Original")
    with pytest.raises(ValueError, match="already exists"):
        svc.create("test-dup", "Duplicate")


def test_empty_id_raises_validation_error():
    svc = ModelsService()
    with pytest.raises(ValueError, match="must not be empty"):
        svc.create("", "Invalid")
