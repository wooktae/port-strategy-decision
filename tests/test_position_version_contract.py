"""Position evaluator version contract tests."""

import pytest

from port_strategy_decision.daily_position_signal_run import (
    DEFAULT_EVALUATOR_VERSION,
    SUPPORTED_EVALUATOR_VERSIONS,
    normalize_evaluator_version,
)


def test_default_position_evaluator_remains_v1():
    assert DEFAULT_EVALUATOR_VERSION == "v1"
    assert normalize_evaluator_version() == "v1"


def test_supported_position_evaluator_versions_are_explicit():
    assert SUPPORTED_EVALUATOR_VERSIONS == {"v1", "v2"}
    assert normalize_evaluator_version("V1") == "v1"
    assert normalize_evaluator_version(" v2 ") == "v2"


def test_unknown_position_evaluator_is_rejected():
    with pytest.raises(ValueError):
        normalize_evaluator_version("v3")