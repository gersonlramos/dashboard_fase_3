# External Integrations

**Analysis Date:** 2026-03-25

## APIs & External Services

**Jira Cloud (Atlassian):**
- Purpose: sole external data source — epics, stories, subtasks, status history, pending items
- Base URL: `https://fcagil.atlassian.net/rest/api/3/`
- Endpoints used:
  - `GET /rest/api/3/search/jql` — paginated JQL search (all three extraction scripts)
  - `GET /rest/api/3/issue/{key}` — individual issue lookup (`app/scripts/script_pendencias.py`)
- Auth: HTTP Basic Auth — email + API token via `requests.auth.HTTPBasicAuth`
- Client: `requests` 2.32.3 (no dedicated Jira SDK)
- SSL: `verify=False` — certificate verification disabled across all scripts (corporate proxy workaround)
- Pagination: cursor-based via `nextPageToken` + `isLast` fields from Jira API v3
- Custom fields used: `customfield_11309` (Start Date), `duedate`
- Changelog expansion: used in `app/scripts/script_atualizacao.py` to extract status transition history

**Jira Project scope:**
- Project key: `BF3E4` (mapped to `FASE_3` internally)
- Epic tracked for pending items: `BF3E4-293`
- Epics with history extraction (9 business domains):
  - `BF3E4-1` (BMC), `BF3E4-9` (COMPRAS), `BF3E4-10` (MOPAR), `BF3E4-17` (CLIENTE)
  - `BF3E4-18` (RH), `BF3E4-19` (FINANCE), `BF3E4-20` (SUPPLYCHAIN)
  - `BF3E4-21` (SHAREDSERVICES), `BF3E4-22` (COMERCIAL)

**Scripts that call Jira (dashboard does NOT call Jira at runtime):**
- `app/scripts/script_atualizacao.py` → writes `app/dados/FASE_3.csv` and `app/dados/processos_seguintes.csv`
- `app/scripts/extrair_historico.py` → writes `app/dados/historico/historico_completo-*.csv`
- `app/scripts/script_pendencias.py` → writes `app/dados/pendencias_BF3E4-293.csv` and `app/dados/historico_BF3E4-293.csv`

## Databases

- None — no relational or NoSQL database in use
- All data persisted as CSV files under `app/dados/` (committed to git)
- The dashboard reads CSV files at startup from `app/dados/` relative to its script location

## File Storage

- Local filesystem only (`app/dados/` and `app/dados/historico/`)
- Files are committed to the repository by `github-actions[bot]` after each scheduled CI run

## Caching

- None detected

## Authentication & Identity

**Jira API authentication:**
- Method: HTTP Basic Auth (email + Atlassian API token)
- Local dev: `EMAIL` and `API_TOKEN` loaded from `.env` file via `python-dotenv`
- CI: `JIRA_EMAIL` and `JIRA_API_TOKEN` GitHub Actions secrets, injected as `EMAIL` / `API_TOKEN`

**Dashboard authentication:**
- None — Streamlit app has no login/auth layer
- Access control relies entirely on Codespaces port forwarding scope

## Environment Variables

| Variable | Purpose | Local source | CI source |
|----------|---------|--------------|-----------|
| `EMAIL` | Jira account email for HTTP Basic Auth | `.env` file | `secrets.JIRA_EMAIL` |
| `API_TOKEN` | Jira API token for HTTP Basic Auth | `.env` file | `secrets.JIRA_API_TOKEN` |

Note: no `.env.example` found in repo; variable names must be inferred from script source.

## Third-party SDKs

- No dedicated Jira SDK — raw REST calls via `requests`
- No cloud provider SDKs (AWS, GCP, Azure)
- No analytics, error tracking, or monitoring SDKs

## CI/CD & Automation

**GitHub Actions** (`.github/workflows/atualizar_dados.yml`):
- Trigger: scheduled cron Mon–Fri at 08:00, 13:00, 17:00, 19:00 UTC (05:00, 10:00, 14:00, 16:00 BRT) + manual `workflow_dispatch`
- Runner: `ubuntu-latest`
- Steps:
  1. `actions/checkout@v4` with write token (`secrets.GITHUB_TOKEN`)
  2. `actions/setup-python@v5` — Python 3.11 with pip cache
  3. `pip install -r requirements.txt`
  4. Run `app/scripts/script_atualizacao.py` (secrets: `EMAIL`, `API_TOKEN`)
  5. Run `app/scripts/extrair_historico.py` (secrets: `EMAIL`, `API_TOKEN`)
  6. Run `app/scripts/script_pendencias.py` (secrets: `EMAIL`, `API_TOKEN`)
  7. `git add app/dados/` → commit with UTC timestamp `[skip ci]` → push (skipped if no diff)

## Webhooks & Callbacks

**Incoming:** None
**Outgoing:** None — integration is polling-based (scheduled pull from Jira, not event-driven)

## Monitoring & Observability

- None — no error tracking service (Sentry, Datadog, etc.)
- Logging: `print()` statements only; visible in GitHub Actions run logs
- No structured logging, no alerting on pipeline failure
- No staleness indicator in the dashboard if CI refresh fails

---

*Integration audit: 2026-03-25*
