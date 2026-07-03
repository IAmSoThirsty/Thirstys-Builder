---- MODULE authorization_invariant ----
EXTENDS Naturals, TLC

VARIABLES identityActive, policyAllows, capabilityAllows, handlerRegistered, executed

Init ==
  /\ executed = FALSE

Execute ==
  /\ identityActive = TRUE
  /\ policyAllows = TRUE
  /\ capabilityAllows = TRUE
  /\ handlerRegistered = TRUE
  /\ executed' = TRUE

Deny ==
  /\ ~(identityActive /\ policyAllows /\ capabilityAllows /\ handlerRegistered)
  /\ executed' = FALSE

Next == Execute \/ Deny

NoUnauthorizedExecution ==
  executed => (identityActive /\ policyAllows /\ capabilityAllows /\ handlerRegistered)

====
