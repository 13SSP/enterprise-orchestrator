"""Domain models and request/response validation schemas for Calculators App.

All monetary and interest rate fields utilize Decimal types for strict precision
and to avoid floating-point inaccuracies inherent in financial calculations.
"""

from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CompoundingFrequency(str, Enum):
    """Supported compounding frequencies with associated annual period counts."""

    ANNUALLY = "ANNUALLY"
    SEMI_ANNUALLY = "SEMI_ANNUALLY"
    QUARTERLY = "QUARTERLY"
    MONTHLY = "MONTHLY"
    DAILY = "DAILY"

    @property
    def periods_per_year(self) -> int:
        """Return the number of compounding periods in a single year."""
        frequency_map = {
            CompoundingFrequency.ANNUALLY: 1,
            CompoundingFrequency.SEMI_ANNUALLY: 2,
            CompoundingFrequency.QUARTERLY: 4,
            CompoundingFrequency.MONTHLY: 12,
            CompoundingFrequency.DAILY: 365,
        }
        return frequency_map[self]


class BaseDomainModel(BaseModel):
    """Base domain model configuration for strict validation across all schemas."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )


class LoanEmiRequest(BaseDomainModel):
    """Input schema for Equated Monthly Installment (EMI) loan calculations."""

    principal: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Total loan principal amount (must be greater than 0)",
        examples=[Decimal("250000.00")],
    )
    annual_interest_rate: Decimal = Field(
        ...,
        ge=Decimal("0.0000"),
        le=Decimal("100.0000"),
        decimal_places=4,
        description="Annual interest rate percentage between 0 and 100",
        examples=[Decimal("7.5000")],
    )
    tenure_months: int = Field(
        ...,
        gt=0,
        le=1200,
        description="Loan repayment tenure in months (1 to 1200 months)",
        examples=[360],
    )


class LoanEmiResponse(BaseDomainModel):
    """Output schema for EMI loan calculations."""

    monthly_emi: Decimal = Field(
        ...,
        decimal_places=2,
        description="Equated Monthly Installment amount",
    )
    total_interest_payable: Decimal = Field(
        ...,
        decimal_places=2,
        description="Total interest payable over the loan tenure",
    )
    total_payment: Decimal = Field(
        ...,
        decimal_places=2,
        description="Total amount payable (principal + interest)",
    )


class CompoundInterestRequest(BaseDomainModel):
    """Input schema for compound interest calculations."""

    principal: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Initial investment principal amount",
        examples=[Decimal("10000.00")],
    )
    annual_interest_rate: Decimal = Field(
        ...,
        ge=Decimal("0.0000"),
        le=Decimal("100.0000"),
        decimal_places=4,
        description="Annual interest rate percentage",
        examples=[Decimal("5.0000")],
    )
    tenure_years: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
        description="Duration of investment in years",
        examples=[Decimal("10.00")],
    )
    compounding_frequency: CompoundingFrequency = Field(
        default=CompoundingFrequency.ANNUALLY,
        description="Frequency of interest compounding per year",
    )
    additional_contribution: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        decimal_places=2,
        description="Regular additional contribution added at each compounding period",
        examples=[Decimal("100.00")],
    )


class CompoundInterestResponse(BaseDomainModel):
    """Output schema for compound interest calculations."""

    principal_amount: Decimal = Field(
        ...,
        decimal_places=2,
        description="Initial principal invested",
    )
    total_contributions: Decimal = Field(
        ...,
        decimal_places=2,
        description="Total periodic contributions made over the investment duration",
    )
    total_interest_earned: Decimal = Field(
        ...,
        decimal_places=2,
        description="Total interest earned over time",
    )
    future_value: Decimal = Field(
        ...,
        decimal_places=2,
        description="Total accumulated future value",
    )


class RoiRequest(BaseDomainModel):
    """Input schema for Return on Investment (ROI) calculations."""

    initial_investment: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        description="Initial cost of the investment",
        examples=[Decimal("1000.00")],
    )
    final_value: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        decimal_places=2,
        description="Final value or gross payout of the investment",
        examples=[Decimal("1500.00")],
    )
    holding_period_years: Optional[Decimal] = Field(
        default=None,
        gt=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
        description="Optional holding period in years for annualized ROI",
        examples=[Decimal("3.00")],
    )


class RoiResponse(BaseDomainModel):
    """Output schema for Return on Investment (ROI) calculations."""

    net_profit: Decimal = Field(
        ...,
        decimal_places=2,
        description="Net financial return (final_value - initial_investment)",
    )
    roi_percentage: Decimal = Field(
        ...,
        decimal_places=4,
        description="Simple percentage return on investment",
    )
    annualized_roi_percentage: Optional[Decimal] = Field(
        default=None,
        decimal_places=4,
        description="Annualized ROI percentage if holding period was provided",
    )
