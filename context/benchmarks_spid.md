# Benchmarks SPID CUP / SPID FEST — Métricas de Referência

**Última atualização:** 07/07/2026
**Contexto:** conta madura (2022-2026), sazonal (6 eventos/ano), público hiper-local (SP + interior + sul MG), fãs de arrancada.

---

## 1. ROAS Alvo por Fase de Campanha

Campanhas SPID têm janela de 30-50 dias com hard cutoffs (viradas de lote, dia do evento). Padrões:

| Fase | Duração típica | ROAS mínimo aceitável | ROAS alvo |
|---|---|---|---|
| Aquecimento | Primeiros 7-14 dias | 10x | 15x |
| Aceleração | Meio da campanha | 8x | 12x |
| Sprint final | Últimos 7-10 dias | 5x | 8x |

**Regra crítica:** durante Aquecimento, NÃO pausar conjunto por ROAS baixo — o algoritmo está aprendendo. Aguardar mínimo 5-7 dias antes de intervir por métrica de conversão.

---

## 2. Cold Start Penalty — Regra Anti-Intervenção Prematura

**Contexto:** conta rodando 6 eventos/ano com pausa entre eventos. Cada retomada de campanha tem cold start.

**Padrão observado nos primeiros 5-7 dias:**
- CPA pode ficar 30-50% acima do "normal"
- ROAS pode ficar abaixo do mínimo aceitável
- Frequência ainda baixa

**Regras:**
- NÃO pausar criativos nos primeiros 5 dias por baixa performance
- NÃO trocar audiência nos primeiros 7 dias
- SÓ intervir se:
  - Zero entrega (impressões = 0) por 48h
  - CPA acima de 3x o benchmark histórico
  - Frequência já saturada (> 8) sem ter começado a converter

Após dia 7, thresholds normais aplicam.

---

## 3. Frequência (janela 7 dias) — Limite por Tier de Audiência

| Tier | Trocar criativo se freq > |
|---|---|
| RMKT quente (Purchase 180D, Initiate Checkout 180D) | 8 |
| RMKT morno (Pageview 180D, Video View 95%) | 7 |
| Lookalike 1% Purchase | 6 |
| Prospecção fria (Interesses) | 4 |

**Ação quando atinge o limite:**
1. Não pausar criativo saturado ainda
2. Subir 2 criativos novos no conjunto (baixa freq média)
3. Deixar Meta redistribuir entrega naturalmente
4. Após 3-5 dias, pausar os saturados que perderam entrega

**Contexto histórico:** freq 20+ observada no Spid Fest 2026 sem colapso de ROAS (Initiate Checkout 180D). Interpretar frequência com o ROAS junto — se ROAS aguenta, freq alta ainda vale.

---

## 4. CPA Dinâmico — Fórmula em Vez de Threshold Fixo

**Motivo:** custo de mídia sobe 15-25% ao ano no Brasil, algoritmo Andromeda penaliza contas sazonais, público saturando naturalmente. CPA absoluto perde referência.

**Fórmula:**

CPA aceitável = Ticket Médio ÷ ROAS Mínimo da Fase

**Exemplos:**

| Fase | Ticket médio | ROAS mínimo | CPA aceitável |
|---|---|---|---|
| Aquecimento | R$110 | 10x | R$11 |
| Aceleração | R$110 | 8x | R$13,75 |
| Sprint final | R$110 | 5x | R$22 |

**Piso absoluto (alerta, não corte):**
- RMKT: alerta se CPA > R$35
- Lookalike: alerta se CPA > R$50
- Prospecção: alerta se CPA > R$80

Piso é gatilho de análise, não ação automática. Contexto sempre importa.

---

## 5. Saturação de Público — Padrão Histórico

**Evidência:** ROAS SPID FEST caiu de 21,8x (2022) → 9x (2026). Não é falha de campanha, é saturação de público hiper-específico ao longo de 4 anos.

**Implicações:**
- Não usar ROAS de anos anteriores como piso — está desatualizado
- ROAS caindo entre eventos é ESPERADO
- Prioridade estratégica: expandir base de público (novos lookalikes, novas geos, criativos que atinjam público não-testado)

**Ação recomendada por evento:**
- Testar 1 audiência nova por campanha (nova origem de lookalike, nova cidade, novo interesse)
- Budget do teste: 5-10% do total
- Manter benchmark histórico só como comparação, nunca como meta

---

## 6. Dias da Semana — Padrão de Conversão

**Ordem de conversão histórica (SPID):**
1. Segunda e Terça — melhores dias, priorizar entrega
2. Quarta e Quinta — desempenho médio
3. Sexta a Domingo — volume menor (público está em eventos, lazer, não comprando online)

**Implicação pra pacing:**
- Não escalar orçamento nos finais de semana
- Considerar reduzir 20-30% do budget de sábado/domingo em favor de seg/ter

---

## 7. Janela de Purchase — Regra Validada

**Purchase 180D venceu Purchase 730D** no SPID FEST 2026. Sinal mais recente = mais eficiente.

**Padrão a seguir:**
- RMKT Purchase: usar janela **180D** por default
- Se ROAS cair abaixo de 8x no meio da campanha, testar reduzir pra **90D**
- Nunca usar acima de 180D em campanhas SPID (público esfria rápido entre eventos)

---

## 8. Cadência de Reporting Adaptativa

**Distância do evento vs frequência do relatório automatizado:**

| Dias até o evento | Cadência |
|---|---|
| > 30 dias | Semanal |
| 15-30 dias | A cada 3 dias |
| 7-14 dias | Diária (08:00 BRT) |
| < 7 dias | 2x/dia (08:00 e 18:00 BRT) |
| Durante evento (2-5 dias) | Diária, foco em resultado do dia + reação |

**Motivo:** proximidade do evento = decisões precisam ser mais rápidas.

---

## 9. Alertas Prioritários

O AdForge deve gerar alerta imediato (não esperar próxima cadência) quando:

- **ROAS geral cai abaixo do mínimo da fase por 48h consecutivas**
- **Gasto diário total ultrapassa +30% do previsto** (risco de estouro de budget)
- **Zero entrega em conjunto ativo por 24h** (falha técnica ou reprovação)
- **Frequência ultrapassa limite tier + ROAS cai simultaneamente** (saturação real, não aparente)
- **Criativo perde 80% da entrega da noite pro dia** (algoritmo desistiu)

---

## 10. Referências Cruzadas

- Meta financeira e distribuição de budget: ver `metas_2026_etapa03.md`
- Estrutura de conjuntos validada: ver `estrutura_campanha.md`
- Regras criativas: ver `politicas_criativas.md`