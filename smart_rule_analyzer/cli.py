import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .analyzer import analyze_rules
from .models import RuleSpec


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze SmartRule RuleSpec v0 JSON")
    parser.add_argument("rules", type=Path, help="path to a RuleSpec v0 JSON array")
    parser.add_argument("--output", type=Path, help="optional output path; defaults to stdout")
    args = parser.parse_args(argv)
    payload = json.loads(args.rules.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        parser.error("rules file must contain a non-empty JSON array")
    rendered = json.dumps(analyze_rules([RuleSpec.from_dict(item) for item in payload]),
                          indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
