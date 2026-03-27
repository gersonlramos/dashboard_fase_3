"""
atualizar_dados.py — Executa todos os scripts de extração em sequência.

Uso:
    python app/scripts/atualizar_dados.py
"""

import subprocess
import sys
import os
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = [
    ("Atualização principal (FASE_3)",   "script_atualizacao.py"),
    ("Pendências / Impedimentos",         "script_pendencias.py"),
    ("Histórico de status (subtarefas)",  "extrair_historico.py"),
    ("Correções",                         "extrair_correcoes.py"),
]


def executar(nome, arquivo):
    caminho = os.path.join(SCRIPTS_DIR, arquivo)
    print(f"\n{'=' * 70}")
    print(f"▶  {nome}")
    print(f"   {caminho}")
    print("=" * 70)
    inicio = time.time()
    resultado = subprocess.run(
        [sys.executable, caminho],
        capture_output=False,   # deixa stdout/stderr fluir direto no terminal
        text=True,
    )
    elapsed = time.time() - inicio
    status = "✓ OK" if resultado.returncode == 0 else f"✗ ERRO (código {resultado.returncode})"
    print(f"\n{status} — {elapsed:.1f}s")
    return resultado.returncode == 0


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  ATUALIZAÇÃO COMPLETA — Dashboard Stellantis Fase 3")
    print("=" * 70)

    total_inicio = time.time()
    resultados = []

    for nome, arquivo in SCRIPTS:
        ok = executar(nome, arquivo)
        resultados.append((nome, ok))

    total = time.time() - total_inicio
    print(f"\n\n{'=' * 70}")
    print(f"  RESUMO  ({total:.1f}s total)")
    print("=" * 70)
    for nome, ok in resultados:
        icone = "✓" if ok else "✗"
        print(f"  {icone}  {nome}")
    print("=" * 70)

    falhas = sum(1 for _, ok in resultados if not ok)
    if falhas:
        print(f"\n  {falhas} script(s) com erro.")
        sys.exit(1)
    else:
        print("\n  Todos os dados atualizados com sucesso.")
        sys.exit(0)
