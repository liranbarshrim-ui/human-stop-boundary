# Assumption status and independence

DAR distinguishes three evidence states:

1. **SELF-DECLARED** — proposed by the project author and not independently validated.
2. **INDEPENDENTLY REVIEWED** — reviewed by a party that did not author the implementation.
3. **EMPIRICALLY VALIDATED** — supported by reproducible evidence under the stated test conditions.

No DAR implementation may upgrade an assumption's status by itself.

The purpose of this separation is to prevent circular validation: DAR cannot establish the external trust assumptions on which its own safety claim depends.

The first external target is therefore not endorsement. It is falsification of the boundary, assumptions, and property.
