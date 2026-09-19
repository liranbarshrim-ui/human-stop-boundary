# Reset Security Contract

`POST /staging/reset` is a destructive state-management operation. It MUST NOT be exposed as an unauthenticated test convenience in a security-boundary evaluation.

The current reference integration intentionally does not yet claim a complete secret-custody boundary: the staging adapter and staging service share an authentication secret in the reference implementation. Therefore this branch does not claim that an attacker controlling the caller process cannot obtain the secret.

Before A11 qualification, reset authorization and secret custody must be tested in the actual deployment topology. A reset must not be able to erase terminal refusal state without an independently authenticated authority action.
