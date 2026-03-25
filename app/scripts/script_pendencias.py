import requests
import csv
import urllib3
import os
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURAÇÕES ---
JIRA_BASE_URL = "https://fcagil.atlassian.net"
URL_ISSUE    = f"{JIRA_BASE_URL}/rest/api/3/issue"
URL_SEARCH   = f"{JIRA_BASE_URL}/rest/api/3/search/jql"

EMAIL     = os.getenv("EMAIL")
API_TOKEN = os.getenv("API_TOKEN")
AUTH      = HTTPBasicAuth(EMAIL, API_TOKEN)

EPIC = "BF3E4-293"

DIR_DADOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dados")
os.makedirs(DIR_DADOS, exist_ok=True)

FILE_CSV        = os.path.join(DIR_DADOS, f"pendencias_{EPIC}.csv")
FILE_HISTORICO  = os.path.join(DIR_DADOS, f"historico_{EPIC}.csv")

FIELDS = "summary,status,priority,duedate,customfield_11309,description,created"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def adf_para_texto(node):
    """Converte Atlassian Document Format (ADF) em texto plano."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_para_texto(i) for i in node)
    if not isinstance(node, dict):
        return ""

    tipo = node.get("type")
    conteudo = node.get("content", [])

    if tipo == "text":
        return node.get("text", "")
    if tipo == "hardBreak":
        return "\n"
    if tipo in ("paragraph", "heading"):
        return "".join(adf_para_texto(i) for i in conteudo) + "\n"
    if tipo == "bulletList":
        return "\n".join(
            f"• {adf_para_texto(item).strip()}" for item in conteudo
        ) + "\n"
    if tipo == "orderedList":
        return "\n".join(
            f"{idx}. {adf_para_texto(item).strip()}"
            for idx, item in enumerate(conteudo, 1)
        ) + "\n"

    return "".join(adf_para_texto(i) for i in conteudo)


def descricao_texto(campo):
    if campo is None:
        return ""
    if isinstance(campo, str):
        return campo.strip()
    return adf_para_texto(campo).strip()


# ---------------------------------------------------------------------------
# Jira API
# ---------------------------------------------------------------------------

def _paginar_jql(jql, expand=None):
    """Executa um JQL com paginação e retorna todas as issues."""
    issues = []
    start = 0
    page = 100

    while True:
        params = {
            "jql": jql,
            "fields": FIELDS,
            "maxResults": page,
            "startAt": start,
        }
        if expand:
            params["expand"] = expand

        resp = requests.get(
            URL_SEARCH,
            params=params,
            auth=AUTH,
            headers={"Content-Type": "application/json"},
            verify=False,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("issues", [])
        issues.extend(batch)
        if start + len(batch) >= data.get("total", 0):
            break
        start += page

    return issues


def buscar_issues_do_epico(epic_key, expand=None):
    """Busca todas as issues da hierarquia do épico (filhos diretos + subtarefas das stories)."""
    # Nível 1: filhos diretos do épico (Stories, Tasks, etc.)
    filhos_diretos = _paginar_jql(
        f'"Epic Link" = {epic_key} OR parent = {epic_key}',
        expand=expand,
    )

    chaves_filhos = [i.get("key") for i in filhos_diretos if i.get("key")]

    # Nível 2: subtarefas das stories (se houver filhos)
    subtarefas = []
    if chaves_filhos:
        # Divide em lotes de 50 para não estourar o JQL
        lote = 50
        for i in range(0, len(chaves_filhos), lote):
            bloco = chaves_filhos[i:i + lote]
            chaves_str = ", ".join(bloco)
            subtarefas += _paginar_jql(
                f"parent in ({chaves_str})",
                expand=expand,
            )

    # Une tudo, evitando duplicatas pela chave
    todas = {i.get("key"): i for i in filhos_diretos + subtarefas}
    return list(todas.values())


def extrair_campos(issue):
    fields = issue.get("fields", {})

    chave      = issue.get("key", "")
    titulo     = fields.get("summary", "")
    status     = (fields.get("status") or {}).get("name", "")
    prioridade = (fields.get("priority") or {}).get("name", "")
    start_date = fields.get("customfield_11309") or ""
    deadline   = fields.get("duedate") or ""
    descricao  = descricao_texto(fields.get("description"))

    return {
        "Chave":      chave,
        "Titulo":     titulo,
        "Status":     status,
        "Prioridade": prioridade,
        "Start Date": start_date,
        "Deadline":   deadline,
        "Descricao":  descricao,
    }


def extrair_historico(issues):
    """Extrai transições de status do changelog de cada issue."""
    rows = []
    for issue in issues:
        chave   = issue.get("key", "")
        titulo  = (issue.get("fields") or {}).get("summary", "")
        criacao = (issue.get("fields") or {}).get("created", "")

        histories = issue.get("changelog", {}).get("histories", [])
        for history in histories:
            autor       = (history.get("author") or {}).get("displayName", "")
            data_mudanca = history.get("created", "")
            for item in history.get("items", []):
                if item.get("field") == "status":
                    rows.append({
                        "Chave":         chave,
                        "Titulo":        titulo,
                        "Data Criacao":  criacao,
                        "Data Mudanca":  data_mudanca,
                        "Status Antigo": item.get("fromString", ""),
                        "Status Novo":   item.get("toString", ""),
                        "Autor":         autor,
                    })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Uma única chamada já com changelog — garante o mesmo conjunto de issues nos dois CSVs
    print(f"Buscando issues do épico {EPIC} (com changelog)...")
    issues = buscar_issues_do_epico(EPIC, expand="changelog")
    print(f"  {len(issues)} issues encontradas.")

    # --- CSV de pendências ---
    rows_pendencias = [extrair_campos(i) for i in issues]
    colunas_pendencias = ["Chave", "Titulo", "Status", "Prioridade", "Start Date", "Deadline", "Descricao"]

    with open(FILE_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=colunas_pendencias)
        writer.writeheader()
        writer.writerows(rows_pendencias)

    print(f"CSV pendências gerado: {FILE_CSV}")

    # --- CSV de histórico de movimentações ---
    rows_historico = extrair_historico(issues)
    colunas_historico = ["Chave", "Titulo", "Data Criacao", "Data Mudanca", "Status Antigo", "Status Novo", "Autor"]

    with open(FILE_HISTORICO, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=colunas_historico)
        writer.writeheader()
        writer.writerows(rows_historico)

    print(f"CSV histórico gerado: {FILE_HISTORICO}")
    print(f"  {len(rows_historico)} transições de status registradas.")


if __name__ == "__main__":
    main()
