# TrafficTrace 1.0.2 alignment plan

## Locked behavior

- Keep `TrafficTrace` and every `TransportObservation` closed to unknown fields.
- Preserve the complete observation shape and its existing trace-ID, ordering, size, transport, and payload-exclusion checks.
- Continue accepting only `instrumented-rpc` and `synthetic-fixture`; only instrumented loopback evidence can support system integration.
- Preserve deterministic features, model generation, hashes, classification, and explicit anomaly/ambiguity abstention.

## Bounded change

1. Require top-level `modelInputVersion` and validate it with the existing bounded-identifier grammar.
2. Add regressions for missing, malformed, and extra top-level fields plus an observation whose `traceId` differs from its trace.
3. Update controlled training and instrumented fixtures, regenerate the deterministic model, and validate the instrumented fixture against the frozen Hub 1.0.2 schema.
4. Pin the final Hub commit, API hash, catalog version, and canonical fixture after the Hub owner freezes them.

## Evidence boundary

This change represents application-level TinyRPC instrumentation and controlled research fixtures. It does not claim operating-system packet capture, home-network interception, real-device accuracy, or real-household coverage.
