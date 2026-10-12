# Traffic Profiling cleanup plan

## Behavior locked before refactoring

- `tests/test_analyzer.py` keeps the deterministic RuleSpec conflict and dependency behavior.
- `tests/test_original_apriori.py` keeps the historical Apriori support, confidence, and pruning behavior.
- The existing eight tests must pass before and after every structural change.

## Changes

1. Add a standard-library profiling core for bounded payload-free RPC traces.
2. Add deterministic model training, edit-distance classification, anomaly, ambiguity, and abstention evidence.
3. Keep synthetic and instrumented sources explicit and reject any unlabelled or oversized trace.
4. Move detector research to `experiments/historical-detector` with source provenance.
5. Transfer synchronization research to the scheduler repository with source provenance; do not present it as profiler core.
6. Remove private machine paths from the current public tree and keep external adapters opt-in.
7. Rewrite public documentation around `SmartHome-Traffic-Profiling` with evidence boundaries.

## Non-goals

- Packet capture, router interception, real-device accuracy, or reproduction of manuscript percentages.
- Treating historical SQL log validation as hardware LL/SC or a lock-free progress proof.
