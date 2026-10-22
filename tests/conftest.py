from __future__ import annotations

import importlib.util

import pytest

# pytest-codspeed registers the `benchmark` marker (and patches the pytest-benchmark `benchmark` fixture) when it is
# installed. We only have those in the dedicated `benchmark` tox environment, so detect their presence here.
HAS_BENCHMARK = importlib.util.find_spec("pytest_benchmark") is not None


def pytest_configure(config: pytest.Config) -> None:
    if not HAS_BENCHMARK:
        # Register the marker ourselves so the rest of the suite doesn't emit "unknown marker" warnings.
        config.addinivalue_line("markers", "benchmark: mark test for benchmarking (requires pytest-benchmark)")


def pytest_runtest_setup(item: pytest.Item) -> None:
    if not HAS_BENCHMARK and item.get_closest_marker("benchmark") is not None:
        pytest.skip("pytest-benchmark is not installed")
