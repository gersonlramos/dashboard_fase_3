import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'dashboard'))

from calculations import monte_carlo_forecast, forecast_linear_range


def test_monte_carlo_returns_percentiles_for_valid_throughput():
    result = monte_carlo_forecast([1, 2, 3], remaining=20, seed=42)
    assert isinstance(result, dict)
    assert isinstance(result['p50'], int)
    assert isinstance(result['p85'], int)
    assert result['p50'] > 0
    assert result['p85'] >= result['p50']


def test_monte_carlo_returns_none_with_insufficient_points():
    result = monte_carlo_forecast([1, 2], remaining=20)
    assert result is None


def test_linear_range_returns_expected_offsets():
    result = forecast_linear_range(ritmo=2.0, remaining=10)
    assert result['atual'] == 5
    assert result['melhor'] == 4
    assert result['pior'] == 8


def test_linear_range_handles_zero_values_safely():
    assert forecast_linear_range(ritmo=0.0, remaining=10) == {
        'melhor': None,
        'atual': None,
        'pior': None,
    }
    assert forecast_linear_range(ritmo=2.0, remaining=0) == {
        'melhor': 0,
        'atual': 0,
        'pior': 0,
    }
