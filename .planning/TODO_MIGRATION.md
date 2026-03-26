# TODO — Acompanhamento Semanal da Migração

**Criado em:** 2026-03-26
**Projeto:** Dashboard Fase 3 — Stellantis
**Atualizar:** semanalmente após extração Jira

---

## Situação Atual (26/03/2026)

| Data Lake | Total | Done | Em Andamento | Em Aberto | % Concluído | Deadline |
|---|---|---|---|---|---|---|
| COMPRAS | 151 | 2 | 60 | 89 | 1.3% | **31/03** |
| COMERCIAL | 1.071 | 0 | 7 | 1.064 | 0% | **31/03** |
| BMC | 20 | 0 | 19 | 1 | 0% | **07/04** |
| CLIENTE | 459 | 0 | 2 | 457 | 0% | 30/04 |
| MOPAR | 402 | 0 | 0 | 402 | 0% | 30/04 |
| RH | 608 | 0 | 1 | 607 | 0% | 30/04 |
| SUPPLY CHAIN | 809 | 0 | 0 | 807 | 0% | 30/04 |
| SHARED SERVICES | 951 | 0 | 0 | 951 | 0% | 30/04 |
| FINANCE | 724 | 0 | 0 | 724 | 0% | 29/05 |
| **TOTAL** | **5.195** | **4** | **89** | **5.102** | **0.1%** | — |

---

## Problemas e Bottlenecks Identificados

| # | Problema | Impacto | Urgência |
|---|---|---|---|
| 1 | 4 impedimentos abertos — 3 já vencidos | Bloqueio de acesso e/ou decisão travando squads | Crítica |
| 2 | COMPRAS e COMERCIAL: ~0% progresso com deadline em dias | Atraso certo nas primeiras entregas | Crítica |
| 3 | SUPPLY CHAIN: 2 Cancelados, 0 em andamento | Possível bloqueio oculto não declarado | Alta |
| 4 | Monte Carlo sem dados suficientes em 8/9 lakes | Forecast do dashboard é projeção linear, não probabilístico | Média |
| 5 | 3.280 itens para 5 lakes entregarem em ~3 semanas (grupo April) | Velocidade necessária muito acima da atual | Alta |
| 6 | FINANCE: 724 itens com 0 started | Risco crescente para deadline de maio | Média |

---

## Impedimentos Abertos

| Chave | Título | Status | Prioridade | Deadline | Situação |
|---|---|---|---|---|---|
| BF3E4-6236 | [Finance] Acesso ao banco de dados Eform | Open | Highest | 30/03/2026 | Vence em 4 dias |
| BF3E4-6226 | Acessos Ferramentas do Cliente | Open | Highest | 23/03/2026 | **Vencido** |
| BF3E4-296 | Comunicar as áreas de negócio responsáveis | Open | Medium | 09/03/2026 | **Vencido** |
| BF3E4-294 | [Shared Services] Retornar a planilha até 05/03 | Open | Medium | 05/03/2026 | **Vencido** |

---

## Semana 1 — 24 a 31/03 (CRÍTICA)

> Deadlines de COMPRAS e COMERCIAL. Impedimentos vencidos em aberto.

- [ ] Avaliar se entrega COMPRAS até 31/03 é realista (2/151 = 1.3% done)
- [ ] Avaliar se entrega COMERCIAL até 31/03 é realista (0/1.071 = 0% done)
- [ ] Escalar / resolver **BF3E4-6226** — Acessos Ferramentas do Cliente (vencido 23/03, Highest)
- [ ] Escalar / resolver **BF3E4-296** — Comunicar áreas de negócio (vencido 09/03, Medium)
- [ ] Escalar / resolver **BF3E4-294** — [Shared Services] planilha (vencido 05/03, Medium)
- [ ] Confirmar ou renegociar deadline de COMPRAS com stakeholders
- [ ] Confirmar ou renegociar deadline de COMERCIAL com stakeholders
- [ ] Registrar decisão de renegociação no Jira (se aplicável)

---

## Semana 2 — 01 a 07/04

> Deadline BMC em 07/04. Avaliar consequências do grupo de 31/03.

- [ ] Resolver **BF3E4-6236** — Finance: Acesso ao banco Eform (deadline 30/03, Highest)
- [ ] Verificar conclusão dos 19 itens "In Progress" do BMC (deadline 07/04)
- [ ] Verificar status real de COMPRAS após deadline — quantos foram entregues?
- [ ] Verificar status real de COMERCIAL após deadline — quantos foram entregues?
- [ ] Avaliar impacto dos atrasos no cronograma geral
- [ ] Investigar por que CLIENTE tem 457 Open e apenas 2 In Progress — bloqueio de acesso?
- [ ] Investigar por que SUPPLY CHAIN tem 2 Canceled e 0 In Progress — bloqueio oculto?

---

## Semana 3 — 08 a 14/04

> Início esperado das entregas do grupo April (CLIENTE, MOPAR, RH, SUPPLY CHAIN, SHARED SERVICES).

- [ ] Confirmar que CLIENTE iniciou migração (meta: ao menos 10% In Progress)
- [ ] Confirmar que MOPAR iniciou migração (meta: ao menos 10% In Progress)
- [ ] Confirmar que RH iniciou migração (meta: ao menos 10% In Progress)
- [ ] Confirmar que SUPPLY CHAIN iniciou migração e investigar os 2 Cancelados
- [ ] Confirmar que SHARED SERVICES iniciou migração
- [ ] Calcular velocidade necessária para entregar os 3.280 itens do grupo até 30/04
  - CLIENTE: ~110 done/semana
  - MOPAR: ~100 done/semana
  - RH: ~152 done/semana
  - SUPPLY CHAIN: ~202 done/semana
  - SHARED SERVICES: ~238 done/semana
- [ ] Verificar se FINANCE pelo menos iniciou planejamento (724 itens, deadline 29/05)

---

## Semana 4 — 15 a 21/04

> Velocidade de entrega do grupo April deve estar visível. Alerta se abaixo da meta.

- [ ] Verificar progresso CLIENTE vs. meta 110 done/semana
- [ ] Verificar progresso MOPAR vs. meta 100 done/semana
- [ ] Verificar progresso RH vs. meta 152 done/semana
- [ ] Verificar progresso SUPPLY CHAIN vs. meta 202 done/semana
- [ ] Verificar progresso SHARED SERVICES vs. meta 238 done/semana
- [ ] Se qualquer lake estiver abaixo de 50% da meta → escalar imediatamente
- [ ] Verificar se Monte Carlo já tem dados suficientes (≥3 dias com Done) para algum lake
- [ ] Identificar novos impedimentos surgidos

---

## Semana 5 — 22 a 28/04 (sprint final grupo April)

> Última semana antes do deadline de 30/04. Foco em finalização.

- [ ] Acompanhar diariamente o progresso dos 5 lakes do grupo April
- [ ] Verificar se FINANCE iniciou migração ativa
- [ ] Confirmar que o forecast do dashboard reflete a realidade para os lakes com dados
- [ ] Preparar relatório de status para entrega de 30/04
- [ ] Listar itens que não serão entregues no prazo e abrir impedimentos

---

## Semana 6 — 29/04 a 05/05 (pós-deadline grupo April)

> Balanço do grupo April. Foco passa para FINANCE.

- [ ] Contabilizar o que foi entregue no prazo vs. atrasado por lake
- [ ] Abrir impedimentos formais para itens não entregues
- [ ] Revisar forecast de FINANCE com dados atualizados
- [ ] Calcular velocidade necessária para FINANCE (724 itens, deadline 29/05 = ~3 semanas)
  - Meta: ~241 done/semana
- [ ] Verificar se novos impedimentos bloqueiam FINANCE

---

## Semana 7+ — Maio (FINANCE e encerramento)

- [ ] Acompanhar FINANCE semanalmente contra meta de 241 done/semana
- [ ] Verificar se todos os lakes anteriores estão 100% Done ou com exceções formalizadas
- [ ] Consolidar relatório final de migração

---

## Velocidade Necessária por Lake (resumo)

| Data Lake | Itens Restantes | Deadline | Semanas Restantes | Meta Semanal |
|---|---|---|---|---|
| COMPRAS | 149 | 31/03 | <1 | ~149 |
| COMERCIAL | 1.071 | 31/03 | <1 | ~1.071 |
| BMC | 20 | 07/04 | ~2 | ~10 |
| CLIENTE | 459 | 30/04 | ~5 | ~92 |
| MOPAR | 402 | 30/04 | ~5 | ~80 |
| RH | 608 | 30/04 | ~5 | ~122 |
| SUPPLY CHAIN | 809 | 30/04 | ~5 | ~162 |
| SHARED SERVICES | 951 | 30/04 | ~5 | ~190 |
| FINANCE | 724 | 29/05 | ~9 | ~80 |

---

*Atualizado em: 2026-03-26*
*Próxima revisão: 31/03/2026*
