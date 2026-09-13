When a decision becomes irreversible under uncertainty,
someone must be required to stop it — by name.

---

# Decision Authority Record (DAR)

Defined by Liran Bar-Shrim

---

Responsibility doesn't disappear.
It concentrates.

---

Either there is a name on the brake —
or the wall stops it.

---

Systems don't fail.
They continue.

---

If no one is defined to stop —
a name will appear after.

---

Control is not the ability to move forward.
Control is the ability to stop.

---

If there is no authority to stop —
you are not managing the event.

You are the event.

---

In any system without a named stop-authority,
accountability will manifest as blame.

---

## DAR v36.14 hardened research release

The repository now contains a versioned hardened DAR security candidate under `dar_v36_14/`.

It includes capability binding, governance/attenuation guards, durable effect intent, recovery integrity, privileged Unix IPC, filesystem boundary checks, optional Linux hardening, live crash-generation testing, anti-rollback anchor interfaces and a verification record.

**Verification in the development environment:** 57 tests passed, 1 optional Landlock test skipped because the host kernel returned `ENOSYS`.

**Important:** v36.14 is a hardened research prototype, not a production certification and does not claim universal control over arbitrary AI systems. Anti-rollback requires a trusted monotonic anchor outside the Store rollback domain; exactly-once external effects remain adapter-dependent.

See [`dar_v36_14/README.md`](dar_v36_14/README.md), [`dar_v36_14/SECURITY.md`](dar_v36_14/SECURITY.md), and [`dar_v36_14/AUDIT_v36_14.md`](dar_v36_14/AUDIT_v36_14.md).

---

Liran Bar-Shrim
https://matrix-audit.com
