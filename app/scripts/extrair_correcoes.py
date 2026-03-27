"""
Script para extrair Correções do Jira (issuetype = "Correção") do projeto BF3E4.
Gera: app/dados/correcoes.csv
"""

import requests
import csv
import urllib3
import os
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

URL   = "https://fcagil.atlassian.net/rest/api/3/search/jql"
EMAIL = os.getenv("EMAIL")
TOKEN = os.getenv("API_TOKEN")
AUTH  = HTTPBasicAuth(EMAIL, TOKEN)

DIR_DADOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados')
os.makedirs(DIR_DADOS, exist_ok=True)
ARQUIVO_SAIDA = os.path.join(DIR_DADOS, 'correcoes.csv')


def buscar_com_paginacao(jql, fields, max_results=100):
    all_issues = []
    next_page_token = None
    while True:
        params = {'jql': jql, 'fields': fields, 'maxResults': max_results}
        if next_page_token:
            params['nextPageToken'] = next_page_token
        resp = requests.get(URL, params=params, auth=AUTH, verify=False)
        if resp.status_code != 200:
            print(f"ERRO {resp.status_code}: {resp.text}")
            break
        data = resp.json()
        all_issues.extend(data.get('issues', []))
        if data.get('isLast', True):
            break
        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            break
    return all_issues


def extrair_texto_adf(campo):
    """Extrai texto plano de um campo no formato ADF (Atlassian Document Format)."""
    if not campo:
        return ''
    if isinstance(campo, str):
        return campo
    textos = []
    def _percorrer(node):
        if isinstance(node, dict):
            if node.get('type') == 'text':
                textos.append(node.get('text', ''))
            for filho in node.get('content', []):
                _percorrer(filho)
        elif isinstance(node, list):
            for item in node:
                _percorrer(item)
    _percorrer(campo)
    return ' '.join(textos).strip()


if __name__ == '__main__':
    print("=" * 70)
    print("EXTRAÇÃO DE CORREÇÕES — JIRA BF3E4")
    print("=" * 70)

    jql = 'project = BF3E4 AND issuetype = "Correção" ORDER BY created DESC'
    fields = 'key,summary,status,created,updated,resolutiondate,assignee,priority,description,comment,parent'

    print("Buscando correções...")
    issues = buscar_com_paginacao(jql, fields)
    print(f"Total encontrado: {len(issues)}")

    if not issues:
        print("Nenhuma correção encontrada.")
        exit(0)

    with open(ARQUIVO_SAIDA, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Chave', 'Titulo', 'Status', 'Data Criacao', 'Data Atualizacao',
            'Data Resolucao', 'Responsavel', 'Prioridade', 'Descricao', 'Historia Pai'
        ])

        for issue in issues:
            flds = issue['fields']
            chave        = issue['key']
            titulo       = flds.get('summary', '')
            status       = (flds.get('status') or {}).get('name', '')
            criacao      = flds.get('created', '')
            atualizacao  = flds.get('updated', '')
            resolucao    = flds.get('resolutiondate') or ''
            responsavel  = (flds.get('assignee') or {}).get('displayName', '')
            prioridade   = (flds.get('priority') or {}).get('name', '')
            descricao    = extrair_texto_adf(flds.get('description'))
            pai          = (flds.get('parent') or {}).get('key', '')

            writer.writerow([
                chave, titulo, status, criacao, atualizacao,
                resolucao, responsavel, prioridade, descricao, pai
            ])

    print(f"\n✓ Arquivo gerado: {ARQUIVO_SAIDA}")
    print(f"✓ Total de correções: {len(issues)}")
    print("=" * 70)
