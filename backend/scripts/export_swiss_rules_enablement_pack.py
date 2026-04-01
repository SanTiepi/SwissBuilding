from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.swiss_rules_spine_service import build_core_swiss_rules_enablement_pack


def _summary_payload() -> dict[str, object]:
    pack = build_core_swiss_rules_enablement_pack()
    return {
        "version": pack.version,
        "generated_at": pack.generated_at.isoformat(),
        "counts": {
            "jurisdictions": len(pack.jurisdictions),
            "authorities": len(pack.authorities),
            "sources": len(pack.sources),
            "rule_templates": len(pack.rule_templates),
            "requirement_templates": len(pack.requirement_templates),
            "procedure_templates": len(pack.procedure_templates),
            "integration_targets": len(pack.integration_targets),
            "guardrails": len(pack.guardrails),
            "watch_plan_entries": len(pack.watch_plan),
        },
        "jurisdiction_levels": dict(Counter(str(item.level) for item in pack.jurisdictions)),
        "watch_cadence": dict(Counter(str(item.cadence) for item in pack.sources)),
        "source_ids": [item.source_id for item in pack.sources],
        "rule_codes": [item.code for item in pack.rule_templates],
        "procedure_codes": [item.code for item in pack.procedure_templates],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the SwissRules enablement pack as JSON."
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Export a compact summary instead of the full pack.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output path. Defaults to stdout.",
    )
    args = parser.parse_args()

    if args.summary:
        payload: dict[str, object] = _summary_payload()
    else:
        pack = build_core_swiss_rules_enablement_pack()
        payload = pack.model_dump(mode="json")

    output = json.dumps(payload, indent=2, sort_keys=True)
    if args.out is None:
        print(output)
        return 0

    args.out.write_text(f"{output}\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
