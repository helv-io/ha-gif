"""Config flow source checks that do not require Home Assistant."""

from __future__ import annotations

import ast
from pathlib import Path

CONFIG_FLOW = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "gif"
    / "config_flow.py"
)


def test_user_step_is_async_without_callback() -> None:
    """async_step_user must not be both @callback and async (HA bug)."""
    tree = ast.parse(CONFIG_FLOW.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if node.name != "async_step_user":
            continue
        decorator_names = [
            ast.unparse(decorator)
            for decorator in node.decorator_list
        ]
        assert "callback" not in decorator_names
        assert not any("callback" in name for name in decorator_names)
        return
    raise AssertionError("async_step_user not found")


def test_options_flow_is_not_registered() -> None:
    """There are no options; do not expose an empty options form."""
    source = CONFIG_FLOW.read_text(encoding="utf-8")
    assert "async_get_options_flow" not in source
    assert "OptionsFlow" not in source
