"""Safe CLI smoke test for Decision entrypoints.

Only argparse --help paths are executed.
Operational functions and database access must never run.
"""

import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


RUNNER = r"""
import importlib.util
import runpy
import sys
from pathlib import Path

repository_root = Path(sys.argv[1]).resolve()
module_name = sys.argv[2]
module_args = sys.argv[3:]

package_name = "port_strategy_decision"
init_path = repository_root / "__init__.py"

spec = importlib.util.spec_from_file_location(
    package_name,
    init_path,
    submodule_search_locations=[str(repository_root)],
)

if spec is None or spec.loader is None:
    raise RuntimeError("Unable to register port_strategy_decision")

package = importlib.util.module_from_spec(spec)
sys.modules[package_name] = package
spec.loader.exec_module(package)

sys.argv = [module_name, *module_args]
runpy.run_module(module_name, run_name="__main__")
"""


MODULES = [
    "port_strategy_decision.daily_buy_signal_run",
    "port_strategy_decision.daily_position_signal_run",
]


def main() -> int:
    for module_name in MODULES:
        command = [
            sys.executable,
            "-c",
            RUNNER,
            str(REPOSITORY_ROOT),
            module_name,
            "--help",
        ]

        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Entrypoint help smoke failed: "
                f"module={module_name}, "
                f"returncode={result.returncode}, "
                f"stdout={result.stdout.strip()}, "
                f"stderr={result.stderr.strip()}"
            )

        if "usage:" not in result.stdout.lower():
            raise RuntimeError(
                f"Entrypoint help output missing usage: {module_name}"
            )

        print(f"ENTRYPOINT_HELP_OK={module_name}")

    print(f"ENTRYPOINT_COUNT={len(MODULES)}")
    print("ENTRYPOINT_SMOKE=SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())