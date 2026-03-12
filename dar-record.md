# DAR Record

A DAR record documents the named human authority
that can stop a system before execution becomes irreversible.

## Template

system:
irreversible_boundary:
stop_authority_name:
stop_authority_role:
escalation_path:
review_date:

## Example

system: automated_credit_approval

irreversible_boundary:
loan_contract_issued_to_customer

stop_authority_name:
Head of Credit Risk

stop_authority_role:
Credit Risk Officer

escalation_path:
Chief Risk Officer

review_date:
2026-03-12