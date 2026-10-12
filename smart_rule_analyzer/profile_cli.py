import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .profiler import ProfileModel, canonical_json, classify


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify a payload-free TinyRPC TrafficTrace using a deterministic profile model")
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--produced-at", default="1970-01-01T00:00:00Z")
    args = parser.parse_args(argv)
    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    model = ProfileModel.from_dict(json.loads(args.model.read_text(encoding="utf-8")))
    args.output.write_text(canonical_json(classify(trace, model, produced_at=args.produced_at)),
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
