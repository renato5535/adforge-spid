# Estrutura de Campanha Validada — SPID CUP / SPID FEST

**Base:** aprendizados 2022-2026, com destaque pra Spid Cup Etapa 02 (2026) e Spid Fest 2026 (recorde histórico).

---

## 1. Estrutura Meta Recomendada

### Campanha A — [ONETIME][CONVERSÃO][SITE] [Nome Evento]

**Objetivo:** Vendas (conversão de compra)
**CBO:** Sim (Advantage Campaign Budget)
**Público:** cold/prospecção

**Conjuntos:**

| Conjunto | Audiência | Prioridade |
|---|---|---|
| 01 - Lkl 1% Purchase 180D | Lookalike da base de compradores 180D | ALTA (validado ROAS 30x em Etapa 02) |
| 02 - Lkl 1% Líder | Lookalike da base "Líder" (compradores mais engajados) | ALTA (CPP R$28 em Spid Fest 2026) |
| 03 - Interesses (teste) | Automobilismo + drag racing + geo restrita | BAIXA — só reativar se topo de funil precisar de reforço |

**Regras específicas:**
- Interesses só rodam se ROAS > 5x nas primeiras 72h — se não, pausar
- Público amplo Andromeda: NÃO USAR em SPID (histórico ruim, ROAS 2,52x em Etapa 02)

### Campanha B — [ONETIME][RMKT][CONVERSÃO][SITE] [Nome Evento]

**Objetivo:** Vendas (conversão de compra)
**CBO:** Sim
**Público:** quente (remarketing)

**Conjuntos (ordem de prioridade validada):**

| Conjunto | Audiência | ROAS histórico |
|---|---|---|
| 00 - Pageview 180D | Visitantes do site últimos 180 dias | 35-68x (Etapa 02) |
| 01 - Video View 95% 180D | Assistiram >=95% de vídeo nos últimos 180 dias | 11-40x |
| 02 - Purchase 180D | Compradores anteriores 180D | Base de tudo, ROAS altíssimo |
| 03 - Initiate Checkout 180D | Iniciaram checkout mas não finalizaram | Fundo de funil crítico |

**Regras específicas:**
- Pageview 180D leva 30-40% do budget da campanha B
- NÃO usar Purchase 730D — janela muito longa, sinal exausto
- Excluir Purchase da audiência de Initiate Checkout (não anunciar pra quem já comprou)

---

## 2. Padrões que NÃO Funcionam (Descartados)

| Elemento | Motivo do descarte |
|---|---|
| Público amplo Andromeda | ROAS 2,52x (Etapa 02) — Andromeda não funciona bem em conta sazonal com pixel frio |
| Purchase 730D | Sinal exausto, ROAS cai comparado a 180D |
| Interesses cold como carro-chefe | Sempre 3-4x pior que RMKT ou Lookalike |
| AddToCart como audiência | Evento nunca disparou no pixel (bug identificado em Spid Fest 2026) — corrigir antes de usar |
| Campanha de Seguidores nos anos 2023-2025 foi removida em 2026 | ROAS geral caiu de ~18x pra ~11x — hipótese: reativar em Etapa 03 pra testar |

---

## 3. Estrutura Google Ads (Se Tracking Destravar)

**Campanha:** Performance Max (PMAX)
**Objetivo:** Vendas
**Budget:** R$300 inicial → escala se ROAS > 5x

**Assets necessários:**
- 14 headlines curtos (até 30 caracteres cada)
- 6 long headlines (até 90 caracteres)
- 6 descriptions (até 90 caracteres, todas diferentes)
- 4-6 imagens verticais + 4-6 quadradas
- 1-6 vídeos verticais/quadrados (existe no YouTube)
- 50 termos de busca (keywords) validados na Etapa 02

**Regra fallback (sem tracking):**
- Migrar pra campanha Discovery ou Display
- Objetivo: alcance qualificado + engajamento
- Keeping alive audience pra futuras campanhas

---

## 4. Estrutura TikTok Ads (Se Tracking Destravar)

**Campanha:** Conversion Campaign (Upgraded Smart+)
**Budget:** R$300 inicial → escala se ROAS > 5x

**Assets necessários:**
- Vídeos verticais 9:16 (15-30s)
- Copies curtas (5 variações)
- Foco em vídeos de carros arrancando + depoimentos reais

**Regra fallback (sem tracking):**
- Migrar pra Traffic ou Community Interaction
- Objetivo: alcance + follows
- Manter conta aquecida pra 2027

---

## 5. Regras de Escalada de Budget

| Situação | Ação |
|---|---|
| ROAS mantém alvo por 3 dias | Escalar +25% (não mais que isso — CBO precisa reaprender) |
| ROAS acima do alvo por 5 dias | Escalar +40% |
| ROAS abaixo do mínimo por 48h | NÃO escalar. Investigar. |
| Frequência acima do tier + ROAS estável | Subir criativo novo, não escalar |

---

## 6. Exclusões Obrigatórias

- Pageview 180D exclui Purchase 180D (evita anunciar pra quem já comprou)
- Initiate Checkout exclui Purchase (mesma lógica)
- Lookalike Purchase exclui Purchase 180D (não vale a pena anunciar pra base atual)
- Interesses exclui todos os RMKT (evita canibalização)

**Regra crítica aprendida no Spid Fest 2026:** exclusões podem estar segurando alcance no fim da campanha. Considerar remover exclusões nos últimos 5-7 dias do evento pra maximizar volume.

---

## 7. Referências

- Métricas de referência: `benchmarks_spid.md`
- Meta financeira e distribuição: `metas_2026_etapa03.md`
- Políticas de criativo: `politicas_criativas.md`
- Histórico de criativos: `historico_criativos.md`
