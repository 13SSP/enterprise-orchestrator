from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

class CalculatorType(str, Enum):
    FINANCIAL = "financial"
    SCIENTIFIC = "scientific"
    STATISTICAL = "statistical"

class CalculatorStatus(str, Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"

class CalculatorSchema(BaseModel):
    """
    Domain entity representing a calculator instance with strict validation.
    """
    model_config = ConfigDict(frozen=True, validate_assignment=True)

    id: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    type: CalculatorType
    status: CalculatorStatus = CalculatorStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('id')
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("ID must be alphanumeric")
        return v

class CalculatorUpdate(BaseModel):
    """
    Schema for mutation operations.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[CalculatorStatus] = None

class DomainException(Exception):
    """
    Base exception for business logic violations.
    """
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)