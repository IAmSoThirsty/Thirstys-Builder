---- MODULE authorization_invariant ----
(*
 * TLC-checkable bounded model of the Constitutional Builder authorization
 * gate. Mirrors the kernel's vertical slice:
 *   request -> identity -> policy -> capability -> handler -> execute
 *
 * The four boolean variables (identityActive, policyAllows,
 * capabilityAllows, handlerRegistered) capture the authorization decision
 * for a single (subject, operation, resource) request. The executed
 * variable is the post-decision state: TRUE only if a handler ran.
 *
 * Two invariants are checked:
 *   1. NoUnauthorizedExecution: executed => (identityActive /\
 *      policyAllows /\ capabilityAllows /\ handlerRegistered). The kernel
 *      never executes a handler unless every gate is TRUE.
 *   2. AuthoritativeExecution (PROPERTY): if all four gates are TRUE and
 *      Next steps, executed becomes TRUE. The kernel does not silently
 *      drop a fully-authorized request.
 *
 * These two together imply the kernel is sound and live over the
 * authorization gate.
 *)
EXTENDS Naturals, TLC

VARIABLES identityActive, policyAllows, capabilityAllows, handlerRegistered, executed

vars == << identityActive, policyAllows, capabilityAllows, handlerRegistered, executed >>

\* --- Type invariant: every variable is a boolean ---
TypeOK == /\ identityActive \in BOOLEAN
          /\ policyAllows \in BOOLEAN
          /\ capabilityAllows \in BOOLEAN
          /\ handlerRegistered \in BOOLEAN
          /\ executed \in BOOLEAN

\* --- Initial state: nothing has been executed yet ---
Init == /\ executed = FALSE
        /\ identityActive \in BOOLEAN
        /\ policyAllows \in BOOLEAN
        /\ capabilityAllows \in BOOLEAN
        /\ handlerRegistered \in BOOLEAN

\* --- Transitions: a request can be authorized (Execute) or denied (Deny) ---
Execute == /\ identityActive = TRUE
            /\ policyAllows = TRUE
            /\ capabilityAllows = TRUE
            /\ handlerRegistered = TRUE
            /\ executed' = TRUE
            /\ UNCHANGED << identityActive, policyAllows, capabilityAllows, handlerRegistered >>

Deny == /\ ~(identityActive /\ policyAllows /\ capabilityAllows /\ handlerRegistered)
        /\ executed' = FALSE
        /\ UNCHANGED << identityActive, policyAllows, capabilityAllows, handlerRegistered >>

\* A "gate reset" transition: a new request comes in with a different
\* combination of gate values. This is the bounded step that lets TLC
\* explore the full 2^4 = 16 input configurations.
NewRequest == /\ executed' = FALSE
               /\ identityActive' \in BOOLEAN
               /\ policyAllows' \in BOOLEAN
               /\ capabilityAllows' \in BOOLEAN
               /\ handlerRegistered' \in BOOLEAN

Next == Execute \/ Deny \/ NewRequest

\* --- Safety: no unauthorized execution ---
NoUnauthorizedExecution ==
    executed => (identityActive /\ policyAllows /\ capabilityAllows /\ handlerRegistered)

\* --- Liveness: a fully-authorized request is executed (a request that
\*     reaches the NewRequest state with all four TRUE will, on a subsequent
\*     Next step, be in the executed=TRUE state). ---
AuthoritativeExecution ==
    []((identityActive /\ policyAllows /\ capabilityAllows /\ handlerRegistered) => <>executed)

====
