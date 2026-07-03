module policy_authorization

abstract sig Effect {}
one sig Allow, Deny extends Effect {}

sig Subject {}
sig Operation {}
sig Resource {}

sig Request {
  subject: one Subject,
  operation: one Operation,
  resource: one Resource
}

sig Policy {
  effect: one Effect,
  subject: lone Subject,
  operation: one Operation,
  resource: lone Resource
}

pred matches[p: Policy, r: Request] {
  (no p.subject or p.subject = r.subject)
  p.operation = r.operation
  (no p.resource or p.resource = r.resource)
}

pred allowed[r: Request] {
  some p: Policy | matches[p, r] and p.effect = Allow
  no p: Policy | matches[p, r] and p.effect = Deny
}

assert ExplicitDenyWins {
  all r: Request | (some p: Policy | matches[p, r] and p.effect = Deny) => not allowed[r]
}
