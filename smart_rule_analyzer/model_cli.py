import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .profiler import canonical_json, train_model


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Train a deterministic traffic medoid model")
    parser.add_argument("--training", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    document = json.loads(args.training.read_text(encoding="utf-8"))
    required = {"schemaVersion", "modelVersion", "threshold", "ambiguityMargin", "labels"}
    if not isinstance(document, dict) or set(document) != required:
        parser.error("training document has unsupported or missing fields")
    labelled_traces = {}
    labelled_patterns = {}
    for entry in document["labels"]:
        if not isinstance(entry, dict) or set(entry) != {"label", "traces", "patterns"}:
            parser.error("each training label requires label, traces, and patterns")
        labelled_traces[entry["label"]] = entry["traces"]
        labelled_patterns[entry["label"]] = entry["patterns"]
    model = train_model(labelled_traces, version=document["modelVersion"],
                        threshold=document["threshold"],
                        ambiguity_margin=document["ambiguityMargin"],
                        label_patterns=labelled_patterns)
    args.output.write_text(canonical_json(model.to_dict()), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
