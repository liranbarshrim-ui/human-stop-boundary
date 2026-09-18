# DAR A11 — Frozen Runtime Audit Environment

## Purpose

This directory defines the reproducible execution environment to be handed to an independent A11 auditor.

The audit target remains the immutable Git commit:

`b0fc0f8f0d719e80a00b27a789ec08c8f5131a81`

The environment is an execution aid only. Building or running it does not itself establish A11 PASS.

## Frozen-target rule

Before any test, the auditor must verify:

```text
EXPECTED_COMMIT=b0fc0f8f0d719e80a00b27a789ec08c8f5131a81
ACTUAL_COMMIT=$(git rev-parse HEAD)
EXPECTED_COMMIT == ACTUAL_COMMIT
```

If the values differ, stop the audit and record `WRONG_FROZEN_COMMIT`.

## Runtime requirements

The auditor should run the image/container with sufficient privileges to perform the requested checks, while preserving an unprivileged test identity for V1. The environment should expose the process namespace, filesystem, IPC namespace and network namespace needed for topology inspection.

Recommended host/runtime capabilities:

- Linux container or VM
- separate unprivileged UID/GID
- process inspection (`/proc`, `ps`)
- socket inspection (`ss` or equivalent)
- filesystem and descriptor inspection
- ability to terminate and restart the target process
- ability to preserve raw stdout/stderr and exit status
- isolated temporary filesystem/state directory

## Required evidence

For each V1–V8 execution, preserve:

- exact frozen commit
- command/invocation
- UID/GID and process identity
- timestamp
- exit status / HTTP status where applicable
- raw stdout/stderr/logs
- filesystem/state observations
- artifact identifier and cryptographic digest where an artifact exists
- auditor attribution

## Vector execution boundary

The supplied repository-local A11 harness remains supporting evidence. The independent auditor must independently execute or inspect each vector and distinguish:

`EXECUTED_AND_OBSERVED`

from

`STATICALLY_INSPECTED`, `NOT_EXECUTED`, or `ENVIRONMENT_UNAVAILABLE`.

No unexecuted vector may be reported as PASS.

## V1–V8 runtime plan

- V1: execute protected-operation attempts under a distinct unprivileged UID/GID.
- V2: independently enumerate and probe applicable sockets, pipes, queues, shared memory and local IPC endpoints.
- V3: inspect and exercise child/helper process delegation, including inherited credentials/descriptors where applicable.
- V4: enumerate and invoke candidate deprecated/debug/internal interfaces where safely reachable.
- V5: establish terminal refusal, terminate the target, restart it, execute recovery/reconciliation, and verify no protected outcome occurs after refusal.
- V6: exercise traversal, absolute paths, symlink substitution, descriptor substitution and TOCTOU conditions where applicable.
- V7: enumerate listeners, module/plugin loading and other side-channel execution mechanisms and test reachable paths.
- V8: capture durable state, establish refusal/anchor state, perform controlled rollback, restart and attempt a fresh protected commit.

## Important limitation

Some vectors require orchestration outside a single process/container, especially restart/recovery and rollback. Those tests must be performed by the auditor using the supplied environment and the surrounding VM/container controls. The Docker image alone must not be represented as completing those tests.
