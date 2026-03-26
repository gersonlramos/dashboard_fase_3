import requests
import csv
import urllib3
import re
from requests.auth import HTTPBasicAuth
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# Desativa avisos de segurança para redes corporativas
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURAÇÕES ---
url = "https://fcagil.atlassian.net/rest/api/3/search/jql"
email = os.getenv("EMAIL")
api_token = os.getenv("API_TOKEN")

projeto = "BF3E4"  # Projeto a buscar
nome_arquivo_sufixo = re.sub(r'[^a-zA-Z0-9-]', '_', projeto)
if projeto == 'BF3E4':
    fase = 'FASE_3'

DIR_DADOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dados')

# Criar diretório de dados se não existir
os.makedirs(DIR_DADOS, exist_ok=True)
    
file_resumo = os.path.join(DIR_DADOS, f"{fase}.csv")

auth = HTTPBasicAuth(email, api_token)

def extrair_data_lake(titulo_historia):
    """Extrai o conteúdo entre colchetes do título da história, removendo números e hífen"""
    if not titulo_historia or titulo_historia == 'N/A':
        return 'N/A'
    
    match = re.search(r'\[(.+?)\]', str(titulo_historia))
    if match:
        conteudo = match.group(1).strip()
        # Remove o hífen e tudo após ele (números, etc.)
        if '-' in conteudo:
            conteudo = conteudo.split('-')[0].strip()
        return conteudo
    return 'N/A'

def classificar_subtarefa(titulo):
    titulo = str(titulo).upper() if pd.notna(titulo) else ""
    
    # Ordem de prioridade na verificação:
    # 1. Story Bug
    if re.search(r'STORY\s*BUG', titulo):
        return "Story Bug"
    
    # 2. Regra de Negócio FMK (Mais específico)
    if "RN-FMK" in titulo:
        return "RN-FMK"
    
    # 3. Regra de Negócio (Busca o termo 'RN' isolado)
    if re.search(r'\bRN\b', titulo):
        return "RN"
    
    return "Desenvolvimento/Outros"

def buscar_com_paginacao(jql, fields, auth, max_results=100):
    all_issues = []
    next_page_token = None

    while True:
        params = {
            "jql": jql,
            "fields": fields,         # pode ser string "key,summary" no GET
            "maxResults": max_results # normalmente 100 é o limite prático
        }
        if next_page_token:
            params["nextPageToken"] = next_page_token

        response = requests.get(url, params=params, auth=auth, verify=False)
        if response.status_code != 200:
            print(f"Erro ao buscar issues: {response.status_code} - {response.text}")
            break

        data = response.json()
        issues = data.get("issues", [])
        all_issues.extend(issues)

        # A paginação correta no /search/jql:
        if data.get("isLast", True):
            break

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            # fallback defensivo: se não veio token, não tem como seguir
            break

    return all_issues

if __name__ == '__main__':
    # --- BUSCAR TODOS OS ÉPICOS DO PROJETO ---
    print(f"Iniciando extração para o projeto: {projeto}")

    print(f"\nEtapa 1: Buscando todos os épicos...")

    jql_epicos = f'project="{projeto}" AND issuetype="Epic"'
    params = {
        'jql': jql_epicos,
        'fields': 'key,summary,customfield_11309,duedate,status',
        'maxResults': 500
    }

    print(f"JQL: {jql_epicos}")
    response_epicos = requests.get(url, params=params, auth=auth, verify=False)

    print(f"Status Code: {response_epicos.status_code}")
    print(f"Resposta bruta (primeiros 500 caracteres): {response_epicos.text[:500]}")

    if response_epicos.status_code != 200:
        print(f"Erro ao buscar epicos: {response_epicos.status_code}")
        print(f"Resposta completa: {response_epicos.text}")
        exit(1)

    response_data = response_epicos.json()
    print(f"Total retornado pelo Jira: {response_data.get('total', 0)}")
    print(f"Issues na resposta: {len(response_data.get('issues', []))}")
    epicos = buscar_com_paginacao(
        jql_epicos,
        "key,summary,customfield_11309,duedate,status",
        auth,
        max_results=100
    )
    total_epicos = response_epicos.json().get('total', 0)
    print(f"Encontrados {len(epicos)} epicos no projeto {projeto} (total: {total_epicos})")

    if len(epicos) == 0:
        print("Nenhum épico encontrado.")
        print(f"Testando acesso ao projeto {projeto}...")
        jql_test = f'project="{projeto}"'
        response_test = requests.get(url, params={'jql': jql_test, 'maxResults': 1}, auth=auth, verify=False)
        if response_test.status_code == 200:
            total_issues = response_test.json().get('total', 0)
            print(f"Projeto {projeto} tem {total_issues} issues no total")
            if total_issues > 0:
                print("Sugestão: O projeto existe mas não tem épicos, ou o tipo 'Epic' tem outro nome no Jira")
        exit(0)

    # Listar épicos encontrados e gerar processos_seguintes.csv
    print("\nÉpicos encontrados:")
    file_epicos = os.path.join(DIR_DADOS, "processos_seguintes.csv")
    with open(file_epicos, mode='w', newline='', encoding='utf-8-sig') as f_ep:
        writer_ep = csv.writer(f_ep)
        writer_ep.writerow(['Chave', 'Titulo', 'Status', 'Start Date', 'Deadline'])
        for epic in epicos:
            f = epic['fields']
            print(f"  - {epic['key']}: {f['summary']}")
            writer_ep.writerow([
                epic['key'],
                f.get('summary', ''),
                (f.get('status') or {}).get('name', ''),
                f.get('customfield_11309') or '',
                f.get('duedate') or '',
            ])
    print(f"Arquivo de épicos gerado: {file_epicos}")

    # --- BUSCAR HISTÓRIAS DE CADA ÉPICO ---
    print(f"\nEtapa 2: Buscando histórias de cada épico...")

    all_stories = []
    story_to_epic = {}  # Mapeamento história -> épico

    for epic in epicos:
        epic_key = epic['key']
        jql_stories = f'parent="{epic_key}" AND issuetype="Story"'
    
        # Usar buscar_com_paginacao para garantir que pegamos TODAS as histórias
        stories = buscar_com_paginacao(
            jql_stories,
            'key,summary,customfield_11309,duedate',
            auth,
            max_results=100
        )

        if stories:
            all_stories.extend(stories)
            # Criar mapeamento história -> épico
            for story in stories:
                story_to_epic[story['key']] = {
                    'epic_key': epic_key,
                    'epic_summary': epic['fields']['summary'],
                    'start_date': story['fields'].get('customfield_11309') or '',
                    'duedate': story['fields'].get('duedate') or '',
                }
            print(f"  {epic_key}: {len(stories)} história(s)")

    print(f"Total de historias encontradas: {len(all_stories)}")

    # --- BUSCAR SUBTAREFAS DE CADA HISTÓRIA ---
    print(f"\nEtapa 3: Buscando subtarefas de cada história...")

    all_subtask_keys = []
    for story in all_stories:
        story_key = story['key']
        jql_subtasks = f'parent="{story_key}"'
    
        # Usar buscar_com_paginacao para garantir que pegamos TODAS as subtarefas
        subtasks = buscar_com_paginacao(
            jql_subtasks,
            'key,summary',
            auth,
            max_results=100
        )
    
        if subtasks:
            subtask_keys = [st['key'] for st in subtasks]
            all_subtask_keys.extend(subtask_keys)
            print(f"  {story_key}: {len(subtasks)} subtarefa(s)")

    print(f"Total de subtarefas encontradas: {len(all_subtask_keys)}")

    if len(all_subtask_keys) == 0:
        print("Nenhuma subtarefa encontrada.")
        exit(0)

    # --- BUSCAR DETALHES DAS SUBTAREFAS ---
    print(f"\nEtapa 4: Carregando detalhes das subtarefas...")

    try:
        issues = []
        batch_size = 100  # Reduzido para respeitar limite do Jira
    
        for i in range(0, len(all_subtask_keys), batch_size):
            batch = all_subtask_keys[i:i+batch_size]
            keys_str = ','.join(batch)
            jql_batch = f'key IN ({keys_str})'
        
            params_batch = {
                'jql': jql_batch,
                'expand': 'changelog',
                'fields': 'summary,status,created,updated,issuetype,priority,assignee,resolutiondate,parent',
                'maxResults': batch_size
            }
        
            response = requests.get(url, params=params_batch, auth=auth, verify=False)
        
            if response.status_code == 200:
                batch_issues = response.json().get('issues', [])
                issues.extend(batch_issues)
                pct = 100*len(issues)//len(all_subtask_keys)
                print(f"  Progresso: {len(issues)}/{len(all_subtask_keys)} ({pct}%)")
            else:
                print(f"  Erro ao buscar lote: {response.status_code}")
    
        print(f"Total de issues coletadas: {len(issues)}")
    
        # --- GERAR RESUMO PARA POWER BI ---
        if len(issues) > 0:
            print(f"\nGerando arquivo de resumo: {file_resumo}")
        
            with open(file_resumo, mode='w', newline='', encoding='utf-8-sig') as f_res:
                writer_res = csv.writer(f_res)
                writer_res.writerow(['Epico', 'Historia', 'Titulo Historia', 'Data-Lake', 'Chave', 'Titulo', 'Status', 'Data Criacao', 'Data Atualizacao', 'Quantidade Subtarefas', 'Categoria_Analise', 'Start Date Historia', 'Deadline Historia'])
            
                for issue in issues:
                    key = issue['key']
                    summary = issue['fields']['summary']
                    status_atual = issue['fields']['status']['name']
                    created_at = issue['fields']['created']
                    updated_at = issue['fields']['updated']
                
                    # Identifica a história pai
                    parent_field = issue['fields'].get('parent', {})
                    parent_key_current = parent_field.get('key', 'N/A')
                    parent_summary = parent_field.get('fields', {}).get('summary', 'N/A') if parent_field else 'N/A'
                
                    # Extrai Data-Lake do título da história
                    data_lake = extrair_data_lake(parent_summary)
                
                    # Busca o épico da história usando o mapeamento pré-criado
                    epic_info = story_to_epic.get(parent_key_current, {})
                    epic_key = epic_info.get('epic_key', 'N/A')
                    epic_summary = epic_info.get('epic_summary', 'N/A')
                
                    # Quantidade de subtarefas
                    quantidade_subtarefas = 0
                
                    # Classificação da subtarefa
                    categoria_analise = classificar_subtarefa(summary)
                
                    start_date_hist = epic_info.get('start_date', '')
                    duedate_hist    = epic_info.get('duedate', '')
                    writer_res.writerow([epic_key, parent_key_current, parent_summary, data_lake, key, summary, status_atual, created_at, updated_at, quantidade_subtarefas, categoria_analise, start_date_hist, duedate_hist])
        
            print(f"Arquivo gerado com sucesso: {file_resumo}")
        
            # Resumo final
            print(f"\n{'='*80}")
            print(f"RESUMO DA EXTRAÇÃO PARA POWER BI - PROJETO {projeto}")
            print(f"{'='*80}")
            print(f"Épicos processados: {len(epicos)}")
            print(f"Histórias encontradas: {len(all_stories)}")
            print(f"Total de subtarefas processadas: {len(issues)}")
            print(f"Arquivo salvo: {file_resumo}")
            print(f"{'='*80}")
        else:
            print(f"Nenhuma issue encontrada.")

    except Exception as e:
        print(f"Erro inesperado: {e}")
