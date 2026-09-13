# Provenance and Evidence Policy

## Purpose

This document defines how claims about Decision Accountability Review (DAR) are to be established and preserved.

## Source of truth

The GitHub repository is the canonical implementation source. The Matrix Audit website is the canonical public research presentation. Neither chat-pasted code nor screenshots are evidence of repository state.

## Evidence chain

`claim -> source -> exact artifact -> fresh checkout -> execution -> observed result -> bounded claim`

A pasted artifact is therefore:

`UNVERIFIED -> repository comparison -> execution -> evidence`

until the chain is completed.

## Version integrity

Each canonical research release should identify:

- version;
- release date;
- repository commit/tag;
- verification result;
- known limitations;
- relevant cryptographic integrity references when available.

## Claim discipline

DAR claims must distinguish among:

1. conceptual doctrine;
2. implementation behavior;
3. tested behavior;
4. deployment-dependent behavior;
5. behavior not established.

A successful test establishes the tested property under the tested conditions. It does not establish universal security or control outside the tested boundary.

## Current bounded scope

DAR's enforcement claims apply only to effects routed through the controlled enforcement boundary. Anti-rollback, exactly-once external effects, pending-intent reconciliation, and operating-system hardening retain the deployment dependencies documented in the repository security record.

## Audit principle

Known failures and unresolved limitations are part of the research record, not material to be hidden from it. Future releases should preserve the history of corrections and changes in `CHANGELOG.md`.

## Author

**Liran Bar-Shrim**  
Independent Researcher  
https://matrix-audit.com
