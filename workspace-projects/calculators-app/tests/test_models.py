import pytest
from datetime import datetime, timezone
from src.models import CalculatorSchema, CalculatorType, CalculatorStatus, DomainException
from pydantic import ValidationError

def test_calculator_creation_success():
    calc = CalculatorSchema(
        id="calc001",
        name="FinancePro",
        type=CalculatorType.FINANCIAL
    )
    assert calc.id == "calc001"
    assert calc.status == CalculatorStatus.ACTIVE
    assert isinstance(calc.created_at, datetime)

def test_calculator_invalid_id():
    with pytest.raises(ValidationError) as exc:
        CalculatorSchema(id="invalid-id!", name="Test", type=CalculatorType.SCIENTIFIC)
    assert "ID must be alphanumeric" in str(exc.value)

def test_immutable_field_validation():
    calc = CalculatorSchema(
        id="calc001",
        name="FinancePro",
        type=CalculatorType.FINANCIAL
    )
    with pytest.raises(ValidationError):
        # Should fail because of frozen=True in ConfigDict
        calc.id = "newid"

def test_status_transition_integrity():
    calc = CalculatorSchema(
        id="calc002",
        name="StatsTool",
        type=CalculatorType.STATISTICAL
    )
    assert calc.status == CalculatorStatus.ACTIVE
    
    # Verify enum validation
    with pytest.raises(ValidationError):
        CalculatorSchema(
            id="calc003",
            name="BadType",
            type="invalid_type"
        )

def test_domain_exception_structure():
    exc = DomainException("Invariant violated", status_code=422)
    assert exc.status_code == 422
    assert str(exc) == "Invariant violated"