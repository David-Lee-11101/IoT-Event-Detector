# Integration contract baseline

This component consumes catalog `1.0.1` from the private integration Hub:

- stable repository ID: `1415109155`
- exact commit: `ff569fdb97a7ad1f2a33665bd3eaceb1bcd28075`
- `contracts/INTEGRATION_API.md` SHA-256: `a6b41f12ea80d2ea4872a34fd7c8b638ad6d4be19e14695ad0bd9dcb99a4365e`

The profiler accepts `TrafficTrace` major version 1 and emits `ProfileEvidence` version `1.0.1`. Shape validation against the canonical Hub schemas remains part of the Hub cold-source runner. `instrumented-rpc` is required for system proof; synthetic fixtures are unit-test evidence only.
