"""Decision module import contract tests.

These tests must not connect to a database or invoke an operational run function.
"""

import importlib


MODULES = [
    "port_strategy_decision.backtest_filter",
    "port_strategy_decision.backtest_market",
    "port_strategy_decision.backtest_sizing",
    "port_strategy_decision.daily_block_watch_builder",
    "port_strategy_decision.daily_block_watch_repository",
    "port_strategy_decision.daily_buy_signal_run",
    "port_strategy_decision.daily_feature_loader",
    "port_strategy_decision.daily_position_evaluator",
    "port_strategy_decision.daily_position_evaluator_v2",
    "port_strategy_decision.daily_position_repository",
    "port_strategy_decision.daily_position_signal_run",
    "port_strategy_decision.daily_repository",
    "port_strategy_decision.daily_signal_builder",
    "port_strategy_decision.daily_validator",
    "port_strategy_common.common_block_watch",
    "port_strategy_common.common_buy_filter",
    "port_strategy_common.common_buy_guard",
    "port_strategy_common.common_buy_sizing",
    "port_strategy_common.common_market",
    "port_strategy_common.common_sell_decision",
]


def test_decision_modules_import_without_execution():
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        assert module is not None