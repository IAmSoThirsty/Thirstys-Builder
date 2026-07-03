# Volume IX - APIs, SDKs, and Interfaces

## Interfaces

- Python API for the reference kernel.
- CLI smoke interface.
- REST-style HTTP API.
- Constrained GraphQL-style query endpoint.
- Server-sent audit event stream.
- Python SDK.
- TypeScript fetch-based SDK.
- PowerShell SDK.
- Protobuf/gRPC service contract.
- Native gRPC service.
- Local JSON gRPC compatibility endpoint.
- Future additional language SDK bindings.

## Inputs and Outputs

Inputs are action request payloads. Outputs are decision payloads, audit event
ids, and replay transcripts.

## Preconditions and Postconditions

Interfaces must preserve the same authorization semantics as the kernel.

## Failure Modes

Schema mismatch, unauthorized caller, version mismatch, transport failure, and
partial response failure.

## Latency and Resources

Transport adapters must publish overhead relative to kernel direct calls.

## Invariants

- APIs cannot bypass kernel authorization.
- SDKs cannot synthesize successful decisions.
- Interface versions are explicit.

## Traceability

Requirements: CBEP-001, CBEP-002.

## Commander Audit

Local HTTP API, constrained query endpoint, audit stream, Python SDK, TypeScript
SDK, PowerShell SDK, protobuf service contract, native gRPC transport, and JSON
gRPC-compatibility endpoint exist. Additional language SDKs remain future
production work.
