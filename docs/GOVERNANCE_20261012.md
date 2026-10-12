# Bounded governance plan

Preserve direction/length medoids, deterministic hashes, source labels, privacy exclusions, and historical research provenance. Baseline: 19 unittest cases passed before edits.

1. Add malformed schema-version and overlong protocol-version regressions; reject these at the same contract boundary that already rejects private metadata.
2. Add malformed medoid-object regressions so all unsupported model input fails with explicit validation rather than incidental exceptions.
3. Rerun unit tests and CLI/schema checks. No feature format or dependency change.

Fallback inventory: no permissive profiling fallback; anomaly/ambiguity rejection is a grounded fail-safe with existing tests. No UI change. No historical-source rewrite.
