# Diagnóstico Pixel Meta — SPID Cup

**Atualizado em:** 08/07/2026 23:40 (corrige dados errôneos de 07/07)
**Conta:** act_881694943239418

---

## Pixels Encontrados na Conta

| ID | Nome | Último Disparo | Criado em |
|----|------|----------------|-----------|
| `867066736318670` | Spid Cup | **nunca** | 31/01/2026 |
| `2522706667879355` | Spid cup-site | 08/07/2026 | 25/10/2022 |

**Pixel ativo: `2522706667879355` (Spid cup-site)**
O pixel `867066736318670` foi criado em jan/2026 e nunca disparou — ignorar completamente.

---

## Pixel: Spid cup-site (`2522706667879355`) — ATIVO

### Status dos Eventos (últimos 90 dias) — DADOS REAIS

| Evento | Disparos | Método | Status |
|--------|----------|--------|--------|
| ViewEtapa | 32.189 | client-side | ✅ |
| ViewContent | 32.187 | client-side | ✅ |
| PageView | 27.779 | client-side | ✅ |
| InitiateCheckout | **4.684** | client-side | ✅ |
| StartInscricao | 4.681 | client-side | ✅ |
| EndInscricao | 704 | client-side | ✅ |
| Purchase | **704** | CAPI (server-side) | ✅ |
| AddToCart | 0 | — | ❌ ausente (evento não existe no fluxo da Agenda) |

> **Nota técnica:** O script de diagnóstico de 07/07 retornou "Purchase = 0" por um bug de leitura
> da estrutura aninhada da API (`/stats?aggregation=event` retorna buckets horários com `data[].data[].value`,
> não `data[].event`). Os valores acima foram verificados com agregação correta em 08/07/2026.

### Funil de Conversão (90d)

```
PageView: 27.779
  → ViewContent / ViewEtapa: ~32.000
    → StartInscricao: 4.681 (16,8% do PageView)
      → InitiateCheckout: 4.684 (100% do StartInscricao — 1:1)
        → Purchase: 704 (15% do InitiateCheckout)
```

O evento `InitiateCheckout` é disparado no momento em que o usuário inicia o formulário de compra (1:1 com `StartInscricao`). `Purchase` chega via CAPI quando o pagamento é confirmado.

---

## Arquitetura Real de Eventos — Agenda Esportiva

| Etapa | Evento(s) | Método |
|-------|-----------|--------|
| Visualização da página do evento | PageView, ViewEtapa, ViewContent | pixel client-side |
| Clique em "Comprar" / início do formulário | StartInscricao, InitiateCheckout | pixel client-side |
| Finalização do formulário | EndInscricao | pixel client-side |
| Confirmação de pagamento | **Purchase** | **CAPI server-side exclusivamente** |
| AddToCart | — | **Não existe** — Agenda não tem carrinho |

> URL da página de confirmação: `agendaesportiva.com.br/inscricao/resumo/{event_id}/{inscricao_id}`

### Status CAPI

| Item | Status |
|------|--------|
| Pixel ID no payload CAPI | ✅ `2522706667879355` |
| Ativo desde | ✅ ~26/02/2026 (após correção de bug duplo) |
| Bug corrigido: `event_time: null` | ✅ Corrigido |
| Bug corrigido: `value: 5` (hardcoded) | ✅ Corrigido |
| `em` / `ph` no payload (hash de email/telefone) | ⚠️ Não confirmado — impacta match rate das audiences |

---

## Diagnóstico — Audiences de Purchase (08/07/2026)

### Configuração das audiences (API confirmada)

| Audience | ID | Pixel | Retention | Tamanho API | Status |
|---|---|---|---|---|---|
| [SITE] Purchase 730D | 120246466183710761 | 2522706667879355 ✅ | 730d | 20* | ✅ OK |
| [SITE] Purchase 180D | 23852023749220760 | 2522706667879355 ✅ | 180d | 20* | ✅ OK |
| [SITE] Purchase 60D | 120227070385330761 | 2522706667879355 ✅ | 60d | 20* | ✅ OK |
| [SITE] Purchase 45D | 120226974062660761 | 2522706667879355 ✅ | 45d | 20* | ✅ OK |
| [SITE] Purchase 14D | 120236841111320761 | 2522706667879355 ✅ | 14d | 20* | ✅ OK |
| Semelhante (1%) - Purchase 730D | 120246466193390761 | — (lookalike) | — | 1.000 | ✅ OK |

*`20` = floor de privacidade da Meta para audiences com menos de 1.000 usuários matched.
Audience existe e está operacional (`delivery_status: 200`).

### Por que o tamanho é "20"?

Com 704 compras via CAPI × taxa de match Meta (~10–20%) = ~70–140 perfis matchados.
Abaixo do threshold de 1.000 → API retorna `20` por privacidade. A audience funciona para targeting.

**A Purchase 730D não está "vazia"** — está configurada corretamente e recebe eventos. O tamanho
é pequeno porque o CAPI só foi corrigido em fev/2026 e o match rate depende de dados como
email_hash/phone_hash no payload (não confirmado).

---

## AddToCart — Ausente Definitivamente

**AddToCart NUNCA existiu na Agenda Esportiva.** Não há carrinho no modelo de ingresso de eventos.
O CJ01 do SPID FEST 2026 que usou AddToCart como audience ficou sem entrega por esse motivo.

**Substituto correto:** `InitiateCheckout` — disparado 4.684 vezes nos últimos 90 dias.

---

## Plano de Ação — Antes da 3ª Etapa (28/08/2026)

| # | Ação | Prioridade | Responsável |
|---|------|-----------|-------------|
| 1 | Criar público **[SITE] InitiateCheckout 30D** no Gerenciador | CRÍTICA | Renato |
| 2 | Criar público **[SITE] InitiateCheckout 90D** no Gerenciador | CRÍTICA | Renato |
| 3 | Nunca criar conjuntos baseados em AddToCart | CRÍTICA | AdForge |
| 4 | Confirmar com Agenda Esportiva se CAPI envia email_hash/phone_hash para melhorar match rate | ALTA | Renato → Guilherme |
| 5 | Usar "Semelhante (1%) - Purchase 730D" como lookalike de compradores | ALTA | AdForge |
| 6 | Verificar se pixel morto `867066736318670` pode ser excluído da conta | BAIXA | Renato |

> Como criar InitiateCheckout 30D: Gerenciador → Públicos → Criar Público →
> Público Personalizado → Site → InitiateCheckout → 30 dias → salvar como "[SITE] InitiateCheckout 30D"
