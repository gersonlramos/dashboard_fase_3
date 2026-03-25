"""
Script para extrair histórico completo de mudanças de status do Jira
Gera apenas o arquivo: historico_completo-{chave}.csv
"""

import requests
import csv
import urllib3
import re
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

# Desativa avisos de segurança para redes corporativas
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

url_base = "https://fcagil.atlassian.net/rest/api/3/search/jql"
email = os.getenv("EMAIL")
api_token = os.getenv("API_TOKEN")

epics = {"BF3E4-1": "BMC", 
        "BF3E4-9": "COMPRAS", 
        "BF3E4-10": "MOPAR", 
        "BF3E4-17": "CLIENTE", 
        "BF3E4-21": "SHAREDSERVICES", 
        "BF3E4-18": "RH",
        "BF3E4-19": "FINANCE",
        "BF3E4-20": "SUPPLYCHAIN",
        "BF3E4-22": "COMERCIAL",    
}

for epic_key, epic_name in epics.items():
    # Opções de tipo_busca: "epic", "story", "jql"
    tipo_busca = "epic"  # epic = busca stories do epic | story = busca subtarefas da story | jql = JQL customizado
    chave = epic_key   # Chave do epic/story (se tipo_busca for "epic" ou "story")
    jql_customizado = ""  # Use quando tipo_busca = "jql" (exemplo: 'project = TOAWS AND status = Done')

    auth = HTTPBasicAuth(email, api_token)

    print("=" * 80)
    print("EXTRAÇÃO DE HISTÓRICO DE MUDANÇAS DE STATUS - JIRA")
    print("=" * 80)
    print(f"Tipo de busca: {tipo_busca}")
    if tipo_busca != "jql":
        print(f"Chave: {chave}")
    else:
        print(f"JQL: {jql_customizado}")
    print("=" * 80)

    # Montar JQL baseado no tipo de busca
    if tipo_busca == "epic":
        jql = f'parent="{chave}"'
        chave_arquivo = chave
        print(f"\n1. Buscando histórias do épico {chave}...")
    elif tipo_busca == "story":
        jql = f'parent="{chave}"'
        chave_arquivo = chave
        print(f"\n1. Buscando subtarefas da história {chave}...")
    elif tipo_busca == "jql":
        jql = jql_customizado
        chave_arquivo = "custom"
        print(f"\n1. Executando JQL customizado...")
    else:
        print(f"ERRO: tipo_busca '{tipo_busca}' inválido. Use 'epic', 'story' ou 'jql'.")
        exit(1)

    # Normalizar nome do arquivo
    nome_arquivo = epic_name
    # Criar diretórios se não existirem
    dir_dados = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados')
    dir_historico = os.path.join(dir_dados, 'historico')
    os.makedirs(dir_historico, exist_ok=True)
    
    arquivo_saida = os.path.join(dir_historico, f"historico_completo-{nome_arquivo}.csv")

    # Buscar todas as issues com changelog em lotes
    print("2. Coletando issues com histórico de mudanças...")

    all_issues = []
    start_at = 0
    max_results = 100

    while True:
        params = {
            'jql': jql,
            'expand': 'changelog',
            'fields': 'summary,status,created',
            'startAt': start_at,
            'maxResults': max_results
        }
        
        response = requests.get(url_base, params=params, auth=auth, verify=False)
        
        if response.status_code != 200:
            print(f"ERRO: {response.status_code} - {response.text}")
            exit(1)
        
        data = response.json()
        issues = data.get('issues', [])
        total = data.get('total', 0)
        
        if not issues:
            break
        
        all_issues.extend(issues)
        print(f"   Coletadas: {len(all_issues)} de {total} issues...")
        
        # Se já coletamos todas as issues disponíveis
        if len(all_issues) >= total:
            break
        
        start_at += max_results

    print(f"\n✓ Total de issues coletadas: {len(all_issues)}")

    if len(all_issues) == 0:
        print("Nenhuma issue encontrada. Verifique o JQL ou a chave informada.")
        exit(0)

    # Processar histórico e gerar CSV
    print(f"\n3. Gerando arquivo de histórico...")

    total_mudancas = 0

    with open(arquivo_saida, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Chave', 'Titulo', 'Data Criacao', 'Data Mudanca', 'Status Antigo', 'Status Novo', 'Autor'])
        
        for issue in all_issues:
            key = issue['key']
            summary = issue['fields']['summary']
            created_at = issue['fields']['created']
            
            # Processar changelog
            histories = issue.get('changelog', {}).get('histories', [])
            
            for history in histories:
                author = history.get('author', {}).get('displayName', 'Desconhecido')
                change_date = history.get('created')
                
                for item in history.get('items', []):
                    # Apenas mudanças de status
                    if item['field'] == 'status':
                        writer.writerow([
                            key,
                            summary,
                            created_at,
                            change_date,
                            item['fromString'],
                            item['toString'],
                            author
                        ])
                        total_mudancas += 1

    print(f"\n✓ Arquivo gerado: {arquivo_saida}")
    print(f"✓ Total de mudanças de status registradas: {total_mudancas}")

    print("\n" + "=" * 80)
    print("EXTRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 80)
