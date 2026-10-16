# Calculators App Requirements

## Overview
A robust financial calculator service providing high-precision calculations for common financial instruments. The service must handle compound interest and loan amortization with strict input validation.

## Scope
- Compound Interest Calculation (Future Value)
- Loan Amortization (Monthly Payments, Total Cost)
- Error handling for invalid financial parameters (e.g., negative interest rates).

## Non-Functional Requirements
- **Statelessness**: No calculation state shall be stored on the server.
- **Precision**: Use Decimal types for all monetary calculations to avoid floating-point errors.
- **Validation**: All inputs must be strictly validated using Pydantic V2.