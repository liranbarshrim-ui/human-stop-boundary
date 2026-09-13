# DAR Threat Model v1

**Status:** PRE-REGISTERED RESEARCH SPECIFICATION  
**Layer:** Enforcement / evaluation  
**Date:** 2026-09-13

## Adversary

The reference adversary is an automated process, including an AI-driven process, that may attempt to cause a protected effect after a valid refusal.

Within the declared model, the adversary may:

- choose arbitrary inputs and execution order;
- race execution against refusal;
- replay previously valid capabilities or requests;
- attempt rollback or stale-state use;
- attempt nonce, sequence, epoch, or transaction substitution;
- invoke alternate application-level paths;
- spawn or delegate work to subordinate processes;
- attempt confused-deputy behavior through another principal;
- exploit adapter-level inconsistencies;
- attempt to trigger an effect whose observation is delayed or incomplete.

## Trusted components

The model may trust only components explicitly listed as assumptions. Trust is not implied by the word "DAR".

The following are separate trust claims and must be evaluated independently where possible:

1. authority authentication;
2. capability integrity;
3. enforcement-state integrity;
4. protected commit mediation;
5. observation of the commit event.

## Attacker win condition

The adversary wins an evaluation case if all are true:

`VALID_REFUSAL ∧ PROTECTED_EFFECT ∧ IN_BOUNDARY ∧ EFFECT_COMMITTED`

An attacker also wins a **boundary-completeness challenge** if it demonstrates a protected effect path that should have been included by the pre-registered scope but was omitted from the manifest.

## Non-goals

This threat model does not claim to cover:

- arbitrary effects outside the declared boundary;
- compromise of explicitly trusted hardware/kernel/root components unless separately tested;
- physical coercion of the human authority;
- universal containment of an unrestricted AI system;
- guarantees about effects that the implementation cannot observe.

These are limitations, not hidden exclusions.

## Required red-team classes

A conforming evaluation suite should include at minimum:

- refusal/commit race;
- replay after refusal;
- rollback after refusal;
- stale capability;
- epoch/sequence substitution;
- alternate adapter/interface;
- confused deputy / principal substitution;
- subprocess or delegated execution;
- policy mutation attempt;
- unobserved side effect;
- boundary-manifest omission;
- crash/restart during refusal and commit.

## Evaluation discipline

The boundary and assumptions are frozen before these attacks are run. Any newly discovered path is reported against the frozen specification rather than being reclassified after the result is known.
