# Human Stop Boundary

A sovereign decision boundary for irreversible automated actions.

## Purpose

This repository defines a human-first stop condition for automated and autonomous systems.

It specifies when execution must pause and responsibility must return to a named human authority.

The boundary is triggered when an action is both:

- Irreversible
- Performed under high uncertainty

## Core Governance Question

Who, by name, has the authority to stop execution before a decision becomes irreversible?

If no named authority exists, the system should not execute.

## Principle

When irreversibility meets uncertainty, the system must stop.

No optimization, fallback, or probabilistic override is permitted.

Continuation requires explicit human acknowledgement and signature.

## Decision Accountability Record (DAR)

The boundary can be documented using a minimal record structure.

system:
irreversible_boundary:
stop_authority_name:
stop_authority_role:
escalation_path:
review_date:

## Example

system: automated_credit_approval

irreversible_boundary: loan_contract_issued_to_customer

stop_authority_name: Head of Credit Risk

stop_authority_role: Credit Risk Officer

escalation_path: Chief Risk Officer

review_date: 2026-03-12

## Design Intent

Stopping is not a failure mode.

It is a deliberately designed state that preserves:

- accountability
- legality
- human agency

Systems that cannot stop are not autonomous.
They are ungoverned.

## Non-Goals

This repository is not an implementation library.

It provides no executable code and does not attempt to automate governance.

The goal is to define a governance boundary that can be inspected, documented, and audited.

## Status

Concept specification.

Provided as a governance reference for inspection and discussion.

## Repository Structure

human-stop-boundary/

README.md – concept and specification  
dar-record.md – record template  
demo/ – visualization example

## License

© 2026 Liran Bar-Sharim. All rights reserved.