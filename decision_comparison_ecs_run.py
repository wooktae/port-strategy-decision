import argparse
import base64
import gzip
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--shadow-jsonl-gzip-b64-env",
        default="DECISION_SHADOW_JSONL_GZIP_B64",
    )
    args = parser.parse_args()

    encoded = os.environ.get(args.shadow_jsonl_gzip_b64_env)
    if not encoded:
        print("DECISION_COMPARISON_ECS_INPUT=MISSING")
        return 2

    try:
        raw = gzip.decompress(base64.b64decode(encoded)).decode("utf-8")
    except Exception as exc:
        print(f"DECISION_COMPARISON_ECS_INPUT=INVALID error={exc}")
        return 2

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        shadow_path = temp / "shadow.jsonl"
        report_path = temp / "report.json"

        shadow_path.write_text(raw, encoding="utf-8")

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "port_strategy_decision.decision_comparator",
                "--shadow-jsonl",
                str(shadow_path),
                "--output",
                str(report_path),
            ],
            check=False,
        )

        if not report_path.exists():
            print("DECISION_COMPARISON_ECS_REPORT=MISSING")
            return 2

        report = json.loads(report_path.read_text(encoding="utf-8"))
        compact = json.dumps(
            report,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        report_b64 = base64.b64encode(
            compact.encode("utf-8")
        ).decode("ascii")

        print(f"DECISION_COMPARISON_REPORT_B64={report_b64}")
        print(
            "DECISION_COMPARISON_ECS_RESULT="
            + str(report.get("result", "INVALID"))
        )

        if proc.returncode == 2:
            return 2

        if proc.returncode != 0:
            return proc.returncode

        return 0


if __name__ == "__main__":
    raise SystemExit(main())
