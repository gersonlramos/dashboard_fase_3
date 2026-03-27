"""
Script para extrair histórico completo de mudanças de status do Jira
Gera apenas o arquivo: historico_completo-{chave}.csv
"""

import requests
import csv
import urllib3
import os
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

url_base  = "https://fcagil.atlassian.net/rest/api/3/search/jql"
email     = os.getenv("EMAIL")
api_token = os.getenv("API_TOKEN")

epics = {
    "BF3E4-1":  "BMC",
    "BF3E4-9":  "COMPRAS",
    "BF3E4-10": "MOPAR",
    "BF3E4-17": "CLIENTE",
    "BF3E4-21": "SHAREDSERVICES",
    "BF3E4-18": "RH",
    "BF3E4-19": "FINANCE",
    "BF3E4-20": "SUPPLYCHAIN",
    "BF3E4-22": "COMERCIAL",
}


def buscar_com_paginacao(jql, fields, auth, expand=None, max_results=100):
    """Busca todas as issues de uma JQL com paginação automática."""
    all_issues = []
    start_at   = 0
    while True:
        params = {
            'jql':        jql,
            'fields':     fields,
            'startAt':    start_at,
            'maxResults': max_results,
        }
        if expand:
            params['expand'] = expand
        response = requests.get(url_base, params=params, auth=auth, verify=False)
        if response.status_code != 200:
            print(f"ERRO: {response.status_code} - {response.text}")
            break
        data   = response.json()
        issues = data.get('issues', [])
        total  = data.get('total', 0)
        if not issues:
            break
        all_issues.extend(issues)
        if len(all_issues) >= total:
            break
        start_at += max_results
    return all_issues


for epic_key, epic_name in epics.items():
    auth = HTTPBasicAuth(email, api_token)

    print("=" * 80)
    print("EXTRAÇÃO DE HISTÓRICO DE STATUS DAS SUBTAREFAS - JIRA")
    print("=" * 80)
    print(f"Épico: {epic_key} - {epic_name}")
    print("=" * 80)

    # 1. Buscar todas as histórias do épico (com paginação)
    print(f"\n1. Buscando histórias do épico {epic_key}...")
    stories = buscar_com_paginacao(
        jql=f'"Epic Link"="{epic_key}"',
        fields='summary,status,created',
        auth=auth,
    )
    print(f"   Coletadas: {len(stories)} histórias.")
    if not stories:
        print("   Nenhuma história encontrada. Verifique o épico informado.")
        continue

    # Diretórios de saída
    dir_dados     = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados')
    dir_historico = os.path.join(dir_dados, 'historico')
    os.makedirs(dir_historico, exist_ok=True)
    arquivo_saida = os.path.join(dir_historico, f"historico_completo-{epic_name}.csv")

    # 2. Buscar subtarefas de cada história e processar changelog
    print(f"\n2. Buscando subtarefas de cada história...")
    total_mudancas = 0

    with open(arquivo_saida, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Chave', 'Titulo', 'Data Criacao', 'Data Mudanca', 'Status Antigo', 'Status Novo', 'Autor'])

        for story in stories:
            story_key = story['key']
            subtasks  = buscar_com_paginacao(
                jql=f'parent="{story_key}"',
                fields='summary,status,created',
                auth=auth,
                expand='changelog',
            )
            print(f"   História {story_key}: {len(subtasks)} subtarefas encontradas.")

            for subtask in subtasks:
                key        = subtask['key']
                summary    = subtask['fields']['summary']
                created_at = subtask['fields']['created']
                histories  = subtask.get('changelog', {}).get('histories', [])
                for history in histories:
                    author      = history.get('author', {}).get('displayName', 'Desconhecido')
                    change_date = history.get('created')
                    for item in history.get('items', []):
                        if item['field'] == 'status':
                            writer.writerow([
                                key,
                                summary,
                                created_at,
                                change_date,
                                item['fromString'],
                                item['toString'],
                                author,
                            ])
                            total_mudancas += 1

    print(f"\n✓ Arquivo gerado: {arquivo_saida}")
    print(f"✓ Total de mudanças de status registradas: {total_mudancas}")
    print("\n" + "=" * 80)
