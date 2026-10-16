"""Unit tests for domain schemas in Calculators App."""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from src.domain.schemas import (
    CompoundingFrequency,
    LoanEmiRequest,
    LoanEmiResponse,
    CompoundInterestRequest,
    CompoundInterestResponse,
    RoiRequest,
    RoiResponse,
)


class TestCompoundingFrequency:
    def test_frequency_enum_values_and_periods(self):
        assert CompoundingFrequency.ANNUALLY.periods_per_year == 1
        assert CompoundingFrequency.SEMI_ANNUALLY.periods_per_year == 2
        assert CompoundingFrequency.QUARTERLY.periods_per_year == 4
        assert CompoundingFrequency.MONTHLY.periods_per_year == 12
        assert CompoundingFrequency.DAILY.periods_per_year == 365


class TestLoanEmiSchemas:
    def test_valid_loan_emi_request(self):
        req = LoanEmiRequest(
            principal=Decimal("100000.00"),
            annual_interest_rate=Decimal("8.50"),
            tenure_months=240,
        )
        assert req.principal == Decimal("100000.00")
        assert req.annual_interest_rate == Decimal("8.50")
        assert req.tenure_months == 240

    def test_loan_emi_request_string_coercion(self):
        req = LoanEmiRequest(
            principal="50000.50",
            annual_interest_rate="5.25",
            tenure_months="60",
        )
        assert req.principal == Decimal("50000.50")
        assert req.annual_interest_rate == Decimal("5.25")
        assert req.tenure_months == 60

    @pytest.mark.parametrize(
        "principal, rate, tenure",
        [
            (Decimal("0.00"), Decimal("5.0"), 12),  # zero principal
            (Decimal("-1000.00"), Decimal("5.0"), 12),  # negative principal
            (Decimal("10000.00"), Decimal("-1.0"), 12),  # negative rate
            (Decimal("10000.00"), Decimal("100.0001"), 12),  # rate > 100
            (Decimal("10000.00"), Decimal("5.0"), 0),  # zero tenure
            (Decimal("10000.00"), Decimal("5.0"), 1201),  # tenure > 1200
        ],
    )
    def test_invalid_loan_emi_request_boundaries(self, principal, rate, tenure):
        with pytest.raises(ValidationError):
            LoanEmiRequest(
                principal=principal,
                annual_interest_rate=rate,
                tenure_months=tenure,
            )

    def test_loan_emi_request_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            LoanEmiRequest(
                principal=Decimal("10000.00"),
                annual_interest_rate=Decimal("5.0"),
                tenure_months=12,
                extra_arg="disallowed",
            )

    def test_valid_loan_emi_response(self):
        res = LoanEmiResponse(
            monthly_emi=Decimal("460.71"),
            total_interest_payable=Decimal("1057.04"),
            total_payment=Decimal("11057.04"),
        )
        assert res.monthly_emi == Decimal("460.71")
        assert res.total_interest_payable == Decimal("1057.04")
        assert res.total_payment == Decimal("11057.04")


class TestCompoundInterestSchemas:
    def test_valid_compound_interest_request_defaults(self):
        req = CompoundInterestRequest(
            principal=Decimal("5000.00"),
            annual_interest_rate=Decimal("6.0"),
            tenure_years=Decimal("5.0"),
        )
        assert req.principal == Decimal("5000.00")
        assert req.annual_interest_rate == Decimal("6.0")
        assert req.tenure_years == Decimal("5.0")
        assert req.compounding_frequency == CompoundingFrequency.ANNUALLY.value
        assert req.additional_contribution == Decimal("0.00")

    def test_valid_compound_interest_request_custom(self):
        req = CompoundInterestRequest(
            principal=Decimal("10000.00"),
            annual_interest_rate=Decimal("7.50"),
            tenure_years=Decimal("10.0"),
            compounding_frequency=CompoundingFrequency.MONTHLY,
            additional_contribution=Decimal("200.00"),
        )
        assert req.compounding_frequency == CompoundingFrequency.MONTHLY.value
        assert req.additional_contribution == Decimal("200.00")

    @pytest.mark.parametrize(
        "principal, rate, tenure, contribution",
        [
            (Decimal("0.00"), Decimal("5.0"), Decimal("1.0"), Decimal("0.00")),  # zero principal
            (Decimal("1000.00"), Decimal("-0.1"), Decimal("1.0"), Decimal("0.00")),  # negative rate
            (Decimal("1000.00"), Decimal("5.0"), Decimal("0.00"), Decimal("0.00")),  # zero tenure
            (Decimal("1000.00"), Decimal("5.0"), Decimal("100.01"), Decimal("0.00")),  # tenure > 100
            (Decimal("1000.00"), Decimal("5.0"), Decimal("1.0"), Decimal("-10.00")),  # negative contribution
        ],
    )
    def test_invalid_compound_interest_boundaries(self, principal, rate, tenure, contribution):
        with pytest.raises(ValidationError):
            CompoundInterestRequest(
                principal=principal,
                annual_interest_rate=rate,
                tenure_years=tenure,
                additional_contribution=contribution,
            )

    def test_invalid_compounding_frequency(self):
        with pytest.raises(ValidationError):
            CompoundInterestRequest(
                principal=Decimal("1000.00"),
                annual_interest_rate=Decimal("5.0"),
                tenure_years=Decimal("1.0"),
                compounding_frequency="BI_WEEKLY",
            )

    def test_valid_compound_interest_response(self):
        res = CompoundInterestResponse(
            principal_amount=Decimal("5000.00"),
            total_contributions=Decimal("1200.00"),
            total_interest_earned=Decimal("850.45"),
            future_value=Decimal("7050.45"),
        )
        assert res.future_value == Decimal("7050.45")


class TestRoiSchemas:
    def test_valid_roi_request_without_holding_period(self):
        req = RoiRequest(
            initial_investment=Decimal("1000.00"),
            final_value=Decimal("1500.00"),
        )
        assert req.initial_investment == Decimal("1000.00")
        assert req.final_value == Decimal("1500.00")
        assert req.holding_period_years is None

    def test_valid_roi_request_with_holding_period(self):
        req = RoiRequest(
            initial_investment=Decimal("1000.00"),
            final_value=Decimal("1500.00"),
            holding_period_years=Decimal("2.50"),
        )
        assert req.holding_period_years == Decimal("2.50")

    @pytest.mark.parametrize(
        "initial, final, period",
        [
            (Decimal("0.00"), Decimal("100.00"), None),  # zero initial investment
            (Decimal("-100.00"), Decimal("100.00"), None),  # negative initial investment
            (Decimal("100.00"), Decimal("-10.00"), None),  # negative final value
            (Decimal("100.00"), Decimal("150.00"), Decimal("0.00")),  # zero holding period
            (Decimal("100.00"), Decimal("150.00"), Decimal("100.01")),  # holding period > 100
        ],
    )
    def test_invalid_roi_request_boundaries(self, initial, final, period):
        with pytest.raises(ValidationError):
            RoiRequest(
                initial_investment=initial,
                final_value=final,
                holding_period_years=period,
            )

    def test_valid_roi_response(self):
        res = RoiResponse(
            net_profit=Decimal("500.00"),
            roi_percentage=Decimal("50.0000"),
            annualized_roi_percentage=Decimal("18.9207"),
        )
        assert res.net_profit == Decimal("500.00")
        assert res.roi_percentage == Decimal("50.0000")
        assert res.annualized_roi_percentage == Decimal("18.9207")
