from __future__ import annotations

from pathlib import Path
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
STACK_PATH = (
    REPO_ROOT / "docs" / "projects" / "claude-now-priority-stack-2026-03-25.yaml"
)


def main() -> int:
    data = yaml.safe_load(STACK_PATH.read_text(encoding="utf-8"))
    print("Claude Now Priority Stack")
    print(f"Date: {data['date']}")
    print()
    for index, step in enumerate(data["immediate_order"], start=1):
        print(f"{index}. {step['step']}")
        if "packs" in step:
            print("   packs:", ", ".join(step["packs"]))
        if "briefs" in step:
            print("   briefs:", ", ".join(str(item) for item in step["briefs"]))
        print("   why:", ", ".join(step["why"] if "why" in step else step["emphasis"]))
        print()

    print("Buyer/demo stack:", ", ".join(str(item) for item in data["buyer_demo_stack"]["briefs"]))
    print("Public-sector stack:", ", ".join(str(item) for item in data["public_sector_stack"]["briefs"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
