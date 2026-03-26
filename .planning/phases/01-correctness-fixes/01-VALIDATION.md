---
phase: 1
slug: correctness-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (≥ 7.x) |
| **Config file** | `pytest.ini` — does not exist yet; Wave 0 must create it |
| **Quick run command** | `pytest tests/test_phase1.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_phase1.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | FIX-01 | unit | `pytest tests/test_phase1.py::test_fix01_ffill -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | FIX-02 | unit | `pytest tests/test_phase1.py::test_fix02_style_map -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 1 | FIX-03 | unit | `pytest tests/test_phase1.py::test_fix03_busday -x` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 1 | FIX-03 | unit | `pytest tests/test_phase1.py::test_fix03b_exception_scope -x` | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 1 | FIX-03 | unit | `pytest tests/test_phase1.py::test_fix03c_historia_guard -x` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 0 | FIX-04 | smoke | `pytest tests/test_phase1.py::test_fix04_pytest_ini -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase1.py` — stubs for FIX-01 through FIX-04 (do NOT import dashboard.py; test logic patterns inline)
- [ ] `pytest.ini` at project root — `[pytest]` section with `filterwarnings = error::FutureWarning`
- [ ] `pytest` added to `requirements.txt` or `requirements-dev.txt`

**Constraint:** Do NOT import `dashboard.py` directly in tests — `st.set_page_config()` runs at module scope and crashes outside Streamlit context. Tests must copy minimal logic inline or mock Streamlit imports.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Detalhes table renders status colors correctly after `style.map()` change | FIX-02 | Requires running Streamlit UI | Run `streamlit run app/dashboard/dashboard.py`, open Detalhes tab, verify colored Status column |
| SLA business-day values match previous loop output | FIX-03 | Requires live CSV data | Compare SLA column values before/after for pending items |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
