"""Import-only smoke test for the Decision container.

This script must never connect to a database or invoke an operational run function.
"""

import importlib
import importlib.util
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_NAME = "port_strategy_decision"

MODULES = [
    "port_strategy_decision.daily_buy_signal_run",
    "port_strategy_decision.daily_position_signal_run",
    "port_strategy_decision.daily_feature_loader",
    "port_strategy_decision.daily_signal_builder",
    "port_strategy_decision.daily_position_evaluator",
    "port_strategy_decision.daily_position_evaluator_v2",
    "port_strategy_common.common_buy_guard",
    "port_strategy_common.common_sell_decision",
]


def register_decision_package() -> None:
    if PACKAGE_NAME in sys.modules:
        return

    init_path = REPOSITORY_ROOT / "__init__.py"

    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        init_path,
        submodule_search_locations=[str(REPOSITORY_ROOT)],
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to create package spec: {PACKAGE_NAME}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    spec.loader.exec_module(module)


def main() -> int:
    register_decision_package()

    print(f"REPOSITORY_ROOT={REPOSITORY_ROOT}")

    for module_name in MODULES:
        module = importlib.import_module(module_name)

        if module is None:
            raise RuntimeError(
                f"Import returned None: {module_name}"
            )

        print(f"IMPORT_OK={module_name}")

    print(f"PYTHON_VERSION={sys.version.split()[0]}")
    print(f"MODULE_COUNT={len(MODULES)}")
    print("CONTAINER_IMPORT_SMOKE=SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())