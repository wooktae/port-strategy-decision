"""Pytest bootstrap for the flat Decision repository layout."""

import importlib.util
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "port_strategy_decision"


def _register_decision_package() -> None:
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


_register_decision_package()