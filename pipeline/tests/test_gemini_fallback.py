from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from pipeline.adapters.gemini import (
    discover_available_flash_model,
    run_with_model_fallback,
)


def test_primary_model_succeeds() -> None:
    runner = MagicMock(return_value="primary_success")
    logger = logging.getLogger("test")

    res = run_with_model_fallback(
        primary_model="model-a",
        fallback_model="model-b",
        runner=runner,
        logger=logger,
    )

    assert res == "primary_success"
    runner.assert_called_once_with("model-a")


def test_fallback_model_used_on_primary_failure() -> None:
    def runner_side_effect(m: str) -> str:
        if m == "model-a":
            raise ValueError("model-a not found")
        return "fallback_success"

    runner = MagicMock(side_effect=runner_side_effect)
    logger = logging.getLogger("test")

    res = run_with_model_fallback(
        primary_model="model-a",
        fallback_model="model-b",
        runner=runner,
        logger=logger,
    )

    assert res == "fallback_success"
    assert runner.call_count == 2
    runner.assert_any_call("model-a")
    runner.assert_any_call("model-b")


def test_dynamic_discovery_used_on_both_failure() -> None:
    mock_client = MagicMock()
    model1 = MagicMock()
    model1.name = "models/gemini-3.0-flash"
    mock_client.models.list.return_value = [model1]

    def runner_side_effect(m: str) -> str:
        if m in ("model-a", "model-b"):
            raise ValueError(f"{m} deprecated")
        return f"discovered_success:{m}"

    runner = MagicMock(side_effect=runner_side_effect)
    logger = logging.getLogger("test")

    res = run_with_model_fallback(
        primary_model="model-a",
        fallback_model="model-b",
        runner=runner,
        logger=logger,
        client=mock_client,
    )

    assert res == "discovered_success:gemini-3.0-flash"
    assert runner.call_count == 3


def test_discover_available_flash_model_prefers_latest_alias() -> None:
    mock_client = MagicMock()
    m1 = MagicMock()
    m1.name = "models/gemini-3.0-flash"
    m2 = MagicMock()
    m2.name = "models/gemini-flash-latest"
    m3 = MagicMock()
    m3.name = "models/gemini-embedding-001"
    mock_client.models.list.return_value = [m1, m2, m3]

    discovered = discover_available_flash_model(mock_client)
    assert discovered == "gemini-flash-latest"
