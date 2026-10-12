# Integration contract baseline

This component consumes the mixed `1.0.2` catalog from the private integration Hub:

- stable repository ID: `1415109155`
- exact commit: `6cb2edb1e9dbfa1572fd6f24f01cd1aef9315f8d`
- `contracts/INTEGRATION_API.md` SHA-256: `60284b3ce107b0948626356dcc6a6841a8c9550dbe8a5970126ad097f1dadf1a`
- canonical `TrafficTrace` fixture SHA-256: `947cab86e7d8317dd52d8236074340eda1c3cf06b3b2046b62138d6616faf5f8`
- `TrafficTrace` schema SHA-256: `a20fb57db13e7fa18578c4562ae908198a4e55a7aac5dd375dc63c98ab0ea4ff`

The profiler accepts corrected `TrafficTrace` version `1.0.2` with a required `modelInputVersion` and complete payload-free `TransportObservation` objects. It emits `ProfileEvidence` version `1.0.1`, which is unchanged in the mixed catalog. Shape validation against the canonical Hub schemas remains part of the Hub cold-source runner. `instrumented-rpc` is required for system proof; synthetic fixtures are unit-test evidence only.
