# Volume XI - Benchmarks and Performance

## Benchmark Targets

- Decision latency.
- Policy evaluation latency.
- Audit append latency.
- Replay validation latency.
- Denial path latency.

## Inputs and Outputs

Inputs are benchmark iterations and representative request fixtures. Outputs are
latency summaries and throughput estimates.

## Preconditions and Postconditions

Benchmarks must use deterministic local fixtures. Results must identify machine
and iteration count when used for certification.

## Failure Modes

Handler variability, file system latency spikes, thermal throttling, and
insufficient sample size.

## Latency Budget

Stage 1 target: p95 below 25 ms in memory and below 100 ms with file audit.

## Resource Requirements

Standard-library Python and local CPU. Production benchmarks must include
cluster, federation, policy, memory, and recovery profiles.

## Invariants

- Benchmarks must not bypass governance gates.
- Benchmark output cannot be used as certification without environment context.

## Traceability

Requirements: CBEP-001, CBEP-003.

## Commander Audit

Stage 1 benchmark harness exists. Production-scale benchmarks remain future
work.
