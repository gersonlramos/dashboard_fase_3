"""
Root conftest.py — loaded by pytest before any test or sub-conftest.

Adds app/dashboard to sys.path so that:
  1. tests/test_calculations.py can `import calculations` directly.
  2. AppTest.from_file(dashboard.py) succeeds when dashboard.py does
     `from calculations import (...)` — AppTest runs in the same process,
     so additions to sys.path here are visible to the exec'd script.
"""
import sys
import os

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), 'app', 'dashboard')
if DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, DASHBOARD_DIR)
