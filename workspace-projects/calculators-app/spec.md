# Calculators App Requirements

## Overview
The Calculators App is a stateless microservice providing financial calculation utilities. It focuses on precision, validation, and clear API contracts for common financial operations like loan amortization and compound interest.

## Business Logic Requirements
1. **Loan EMI Calculation**: Calculate Equated Monthly Installments based on principal, annual rate, and tenure.
2. **Compound Interest**: Calculate future value based on compounding frequency.
3. **Investment ROI**: Calculate simple Return on Investment percentages.

## Technical Constraints
- Use **Pydantic V2** for all input/output validation.
- **Statelessness**: No database required; all inputs provided in the request.
- **Precision**: Use `Decimal` types for all monetary calculations to avoid floating-point errors.