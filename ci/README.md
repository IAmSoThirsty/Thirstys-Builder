# CI

Future CI must run:

- `python -m unittest discover -s tests`
- `python scripts/validate_repository.py`
- `python benchmarks/benchmark_kernel.py --iterations 1000`

CI must publish test, traceability, benchmark, and certification evidence.
