# Gap Tracking — Google Ads / GA4 e TikTok Ads
# SPID Cup AdForge — Análise de Cobertura de Conversões

**Criado em:** 07/07/2026  
**Contexto:** AdForge gerencia 100% Meta Ads desde Mai/2026. Google e TikTok não recebem
dados de conversão do SPID Cup, gerando cegueira analítica e impossibilidade de escala
nessas plataformas.

---

## Situação Atual

| Plataforma | Pixel/Tag | Conversões | Públicos | Status |
|------------|-----------|------------|----------|--------|
| **Meta Ads** | ✅ Pixel "Spid cup-site" ativo (disparou 07/07) | ✅ Purchase + InitiateCheckout via Agenda | 27 públicos mapeados | **Operacional** |
| Google Analytics 4 | ❓ Desconhecido (não instalado pelo AdForge) | ❌ Sem dados confirmados | ❌ | **Gap desconhecido** |
| Google Ads | ❓ Desconhecido | ❌ Nenhuma campanha ativa | ❌ | **Gap total** |
| TikTok Ads | ❌ Sem pixel | ❌ Sem conversões | ❌ | **Gap total** |

---

## Google Analytics 4 — Gap Analysis

### Eventos que DEVEM ser recebidos

| Evento GA4 | Trigger | Método Recomendado | Prioridade |
|-----------|---------|-------------------|-----------|
| `purchase` | Confirmação de compra na Agenda | GTM + dataLayer OU Measurement Protocol | **CRÍTICA** |
| `begin_checkout` | Clique em "Comprar" na Agenda | GTM + dataLayer | ALTA |
| `view_item` | Visualização da página do evento | GTM automático | MÉDIA |
| `page_view` | Toda página visitada | GTM automático | MÉDIA |
| `add_to_cart` | **Não existe no fluxo da Agenda** — skip | — | IGNORAR |

### Implementação (ordem de prioridade)

**Opção A — GTM na página do evento (1–2 dias, mais rápida):**
1. Verificar com suporte Agenda Esportiva se permitem GTM no domínio do evento
2. Criar container GTM para o domínio agendaesportiva.com.br
3. Instalar GA4 configuration tag com Measurement ID (G-XXXXXXXX)
4. Trigger `begin_checkout`: botão "Comprar" → dataLayer push
5. Trigger `purchase`: página de confirmação → dataLayer push com `transaction_id`, `value`, `currency: "BRL"`

**Opção B — Measurement Protocol GA4 (server-side, mais robusta):**
```
POST https://www.google-analytics.com/mp/collect?measurement_id=G-XXX&api_secret=XXX
Body: {
  "client_id": "{agenda_user_id}",
  "events": [{"name": "purchase", "params": {
    "transaction_id": "{pedido_id}",
    "value": 180.00, "currency": "BRL",
    "items": [{"item_name": "3ª Etapa SPID Cup 2026", "price": 180.00, "quantity": 1}]
  }}]
}
```
Requer webhook de confirmação de compra da Agenda Esportiva.

**Opção C — Make.com sem acesso ao backend:**
1. Agenda Esportiva envia email de confirmação de compra
2. Make.com (Gmail trigger) parseia o email e extrai valor/evento/ID
3. Make.com chama Measurement Protocol GA4
4. Make.com chama Meta CAPI simultaneamente (bônus: melhora event match quality)

### Primeira pergunta ao suporte Agenda Esportiva
```
"Vocês suportam Google Tag Manager na página do evento?"
"Vocês têm webhooks de order completed (confirmação de compra)?"
"Qual o domínio exato da página de checkout/confirmação?"
```

---

## Google Ads — Gap Analysis

### Por que não rodamos hoje
1. Sem tag de conversão → impossível otimizar campanha por purchase
2. Sem RLSA lists (Remarketing Lists for Search Ads)
3. Budget concentrado 100% Meta (ROAS histórico validado)
4. YouTube Ads: vídeos existem mas não há campanha

### Eventos para Google Ads (quando ativar)

| Evento | Trigger | Valor | Método |
|--------|---------|-------|--------|
| "Compra Ingresso" | Confirmação de compra | Dinâmico | gtag.js OU import GA4 |
| "Início Checkout" | Botão "Comprar" | 0 (micro-conv.) | gtag.js |
| Audience "Compradores" | Purchase completo | — | Import GA4 audiences |

### Setup mínimo para YouTube (se decidir testar na 3ª Etapa)
1. Conta Google Ads vinculada ao email do Renato
2. Tag de conversão Google Ads instalada via GTM (mesma tag do GA4)
3. Upload do ad-18 no YouTube (canal SPID Cup)
4. Campanha Video Action: in-market "Motorsport events" + RLSA visitantes
5. Budget teste: R$500–1.000, medir CPP vs. Meta

---

## TikTok Ads — Gap Analysis

### Por que pode ser relevante
- Audiência 18–35 BR (overlap com entusiastas motorsport)
- CPM historicamente 30–50% menor que Meta no Brasil
- Conteúdo de arrancada performa organicamente no TikTok
- ad-18 (vídeo arquibancada) tem formato nativo TikTok

### Eventos para TikTok Pixel

| Evento TikTok | Equivalente Meta | Trigger |
|--------------|-----------------|---------|
| `CompletePayment` | Purchase | Confirmação de compra |
| `InitiateCheckout` | InitiateCheckout | Botão "Comprar" |
| `ViewContent` | ViewContent | Página do evento |

### Implementação TikTok

**Passo 1 — Criar conta e pixel:**
```
business.tiktok.com → Events Manager → Web Events → Create Pixel
Obter: Pixel ID + Access Token (para Events API server-side)
```

**Passo 2 — Instalar via GTM (se Agenda permitir):**
```javascript
// Tag customizada HTML no GTM
ttq.load('TIKTOK_PIXEL_ID');
ttq.page();
// Na trigger de purchase:
ttq.track('CompletePayment', {
  content_name: '3ª Etapa SPID Cup 2026',
  currency: 'BRL', value: 180.00, quantity: 1
});
```

**Passo 3 — Events API (server-side via Make.com):**
```
POST https://business-api.tiktok.com/open_api/v1.3/pixel/track/
Headers: Access-Token: {TOKEN}
Body: {"pixel_code": "ID", "event": "CompletePayment",
       "properties": {"value": 180.00, "currency": "BRL"}}
```

### Teste piloto recomendado: 3ª Etapa 2026
- Budget: R$500–1.000
- 1 campanha conversão (objetivo: CompletePayment)
- Upload vídeo arquibancada + 2 vídeos de largada
- Target: Broad BR 18–45 + interesses Motorsport
- KPI: CPP < R$8 (benchmark Meta histórico)

---

## Prioridade de Implementação

| # | Ação | Plataforma | Esforço | Impacto | Prazo |
|---|------|-----------|---------|---------|-------|
| 1 | Contatar Agenda Esportiva (GTM + webhooks) | Todas | Baixo | Muito Alto | Jul/26 semana 1 |
| 2 | Implementar GA4 purchase via Measurement Protocol ou GTM | GA4 | Médio | Muito Alto | Jul/26 semana 2–3 |
| 3 | Criar listas de remarketing GA4 → Google Ads | Google Ads | Médio | Alto | Jul/26 semana 3 |
| 4 | Criar TikTok Business + Pixel | TikTok | Baixo | Médio | Jul/26 semana 2 |
| 5 | Instalar TikTok Pixel via GTM | TikTok | Médio | Médio | Jul/26 semana 3 |
| 6 | Testar TikTok Ads na 3ª Etapa (R$500–1k) | TikTok | Médio | Médio | Ago/26 |
| 7 | Testar YouTube Ads na 3ª Etapa | Google Ads | Alto | Médio | Ago/26 (opcional) |

---

## Descoberta — Página de Integrações (07/07/2026)

A página de integrações do SPID FEST 2026 (ID 21688) mostra **Google Analytics, TikTok e Facebook como ✅ Conectado**.

---

## IDs Confirmados pelo Renato (07/07/2026) ✅

| Plataforma | ID | Status |
|-----------|-----|--------|
| Google Analytics 4 | `G-E6VR1KCHYK` | Configurado na Agenda — IDs do SPID Cup ✅ |
| TikTok Pixel | `CV4QP1RC77U997N5C01G` | Configurado na Agenda — IDs do SPID Cup ✅ |
| Meta Pixel | `2522706667879355` | "Spid cup-site" — Funcional ✅ |

**Hipótese de "ID errado / Agenda Off Road" descartada.** Os IDs são os corretos do SPID Cup.

---

## Diagnóstico Real — Causa Raiz Identificada (07/07/2026)

### O que o GA4 está recebendo (últimos 28 dias, inclui SPID FEST 2026)

| Evento | Contagem | Tipo |
|--------|----------|------|
| `page_view` | 62.943 | Browser client-side ✅ |
| `ViewEtapa` | 16.135 | Customizado Agenda ✅ |
| `StartInscricao` | 1.985 | Customizado Agenda ✅ |
| **`purchase`** | **0** | **Server-side — AUSENTE ❌** |
| Receita total | R$ 0,00 | — |

### Linha do tempo do problema

- **SPID FEST 2025:** GA4, TikTok e Meta funcionavam com conversões e valor.
- **Início 2026:** Atualização de código na Agenda quebrou Purchase nas 3 plataformas.
- **~26/02/2026:** Meta CAPI corrigida (bugs: `event_time: null` + `value: 5` hardcoded).
- **07/07/2026:** GA4 e TikTok **ainda não corrigidos** — o bug permanece.

### Causa

O código que envia conversão para GA4 (Measurement Protocol) e TikTok (Events API) na página de confirmação de compra tem o mesmo tipo de bug que quebrou o Meta, ou foi desabilitado na mesma atualização e nunca reativado. **Não é problema de ID — é bug no backend da Agenda.**

## Dependência Bloqueante (ATUALIZADA 07/07/2026)

**Ação para Renato:** Contatar Guilherme com a mensagem:

> "Guilherme, até o SPID FEST 2025 o Google Analytics (ID: G-E6VR1KCHYK) e o TikTok (Pixel: CV4QP1RC77U997N5C01G) recebiam dados de conversão normalmente. Em 2026, pararam de registrar eventos de Purchase — o mesmo problema que afetou a Meta e foi corrigido em fevereiro. O GA4 ainda recebe pageviews e ViewEtapa, mas o Purchase não chega. Precisamos corrigir isso antes da 3ª Etapa (agosto/2026). Podem verificar o código que envia o evento de conversão para GA4 e TikTok na página de confirmação de compra?"

---

## Referências
- Pixel Meta ativo: "Spid cup-site" `2522706667879355` (disparou 07/07/2026 23:37)
- Pixel Meta inativo: "Spid Cup" `867066736318670` (nunca disparou — verificar se campanhas usam este)
- Diagnóstico completo: `~/.adforge/context/pixel_diagnostic.md`
- Histórico de públicos: `~/.adforge/context/historico_publicos.md`
- Crossref Meta × Agenda: `~/.adforge/reports/crossref-spid.json`
