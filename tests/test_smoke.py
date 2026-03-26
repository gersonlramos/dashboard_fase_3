"""
AppTest smoke test (TEST-07): verifies dashboard loads without exception.
"""
import os
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

DASHBOARD_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'app', 'dashboard', 'dashboard.py'
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear Streamlit cache before and after each test to avoid stale state."""
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def test_dashboard_loads_without_exception():
    at = AppTest.from_file(DASHBOARD_PATH, default_timeout=60)
    at.run()
    assert not at.exception, (
        f"Dashboard raised an exception during AppTest run: {at.exception}"
    )
