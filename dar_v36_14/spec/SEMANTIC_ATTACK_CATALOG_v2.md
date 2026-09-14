# DAR Semantic Attack Catalog v2

Status: PRE-REGISTERED ATTACK PLAN

These attacks target the formal semantics rather than relying on ambiguity between DAR state and external-world state.

## S-01 — Crash after external effect

Trace:
`authorized execution -> external side effect -> crash -> refusal -> REFUSED`

Expected result: FAIL if the side effect is the declared protected outcome and the refusal was ordered before the model claims the effect was prevented. Otherwise classify as a durability/atomicity limitation.

## S-02 — Epoch/person substitution

Attempt to produce an epoch transition without an authenticated authorized human refusal, or to cause an unauthorized principal to appear as the refusing principal.

Expected result: the transition MUST NOT qualify as `valid_refusal`.

## S-03 — WRITE/outcome substitution

Construct an irreversible outcome through an action that is not itself the declared WRITE syscall but is causally capable of producing the protected outcome.

Expected result: either the outcome is inside A1's independently audited protected boundary, or the claim is explicitly out of scope.

## S-04 — Stop latency / availability

Hold or stall an adapter operation while a valid refusal is attempted.

Expected result: document whether the refusal is merely eventually ordered, or whether the deployment claims bounded/immediate stopping. The core safety property MUST NOT silently imply an availability guarantee.

## S-05 — Store/journal/external divergence

Crash at each durability boundary between Store state, PREPARED/COMMITTED/REFUSED journal state, and external effect state.

Expected result: no state combination may be interpreted as proof that an external effect did not happen unless the protocol actually establishes that fact.

## Verdict discipline

A failed attack against the implementation is not a PASS for the complete DAR v2 claim unless A1, A9, authenticated refusal semantics, and the protected-effect definition are independently satisfied.

Conversely, a crash-induced world-state divergence is a core failure if the public claim is stated as prevention of the real-world protected outcome rather than prevention of a DAR-internal commit.
