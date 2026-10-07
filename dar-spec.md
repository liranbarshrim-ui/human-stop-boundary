DAR™ — Decision Authority Record (DAR)  
**Review / audit layer:** DAR review and Boundary Audit  
Specification v1.0  
Status: Public / Reference  

---

### 1. Definition

A **Decision Authority Record** is the canonical DAR governance construct.

It establishes a named individual with the authority and obligation to stop execution before a decision becomes irreversible under uncertainty.

---

### 2. Core Principle

When a decision becomes irreversible under uncertainty, someone must be required to stop it — by name.

---

### 3. Problem

Most governance systems define:
- what should happen  
- how decisions are executed  

They do not define:
- who must stop when execution should not proceed  

---

### 4. Requirement

A valid Decision Authority Record must include:

1. Irreversibility threshold  
2. Named individual (by name, not role)  
3. Stop authority (non-deferrable)  
4. Obligation to act  
5. Defined trigger conditions  

---

### 5. Constraint

- Not a committee  
- Not a policy  
- Not a role  
- Not post-incident reconstruction  

---

### 6. Assertion

If the name must be reconstructed after the event, the Decision Authority Record did not exist.

---

### 7. Scope

DAR applies where:
- decisions are automated or semi-automated  
- outcomes may become irreversible  
- uncertainty cannot be fully modeled  

A DAR review or Boundary Audit may then test whether the named authority is actually binding and whether alternate paths can bypass the protected boundary.

---

### 8. Status

DAR is a governance construct and named-authority record. Its review/audit layer tests whether the claimed authority is structurally effective. The Human Stop Boundary is the associated enforcement-boundary research prototype.

---

© Liran Bar-Shrim  
All rights reserved.
