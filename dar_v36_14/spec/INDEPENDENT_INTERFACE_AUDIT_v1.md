# DAR Independent Interface / Escape Audit v1

**Purpose:** establish, independently of DAR's own enforcement code, whether every path capable of producing the declared protected `WRITE` effect is routed through the registered enforcement boundary.

**Important:** this document is a protocol/template, not evidence that the audit has been completed.

## Required audit scope

The auditor must enumerate and inspect, for the frozen deployment:

1. all processes and OS identities that can reach the protected effect;
2. all IPC endpoints, sockets, pipes, queues, shared-memory paths, and helper processes;
3. all filesystem paths and file descriptors capable of producing the protected write;
4. all adapters and privileged helpers that can commit the effect;
5. all importable APIs and direct-call paths, including deprecated or removed interfaces;
6. all startup, recovery, migration, and reconciliation paths;
7. race-condition and time-of-check/time-of-use paths;
8. any external tool, subprocess, plugin, or side-channel capable of producing the effect.

## Independence requirements

The auditor must not rely solely on DAR-authored assertions, unit tests, or the presence/absence of a public method. Evidence should include deployment configuration, OS permissions/identity boundaries, reachable endpoints, and adversarial attempts to invoke discovered paths outside the registered interface.

## Required conclusion

The auditor must issue one of:

- **COMPLETE:** no unregistered path capable of producing the declared protected effect was found within the frozen deployment scope;
- **INCOMPLETE:** at least one unregistered path exists;
- **AMBIGUOUS:** available evidence is insufficient to establish completeness.

Only **COMPLETE** satisfies A1 for a v2 PASS. The result must be preserved as an external artifact and linked from the corresponding conformance record.
