# Tracking — Histórico do Diagnóstico com Agenda Esportiva

**Criado em:** 07/07/2026  
**Fonte:** Conversa WhatsApp com Guilherme (Agenda Esportiva Off Road/Esportiva & Big...) — Fev/Mar 2026  
**Período coberto:** 02/02/2026 a 04/03/2026 (+ última mensagem em 15/06/2026)

---

## Contexto

Em fevereiro de 2026, o Renato identificou que Meta Ads, TikTok e Google Analytics não estavam recebendo dados de vendas, purchase ou valor de ROAS. Iniciou contato com o suporte técnico da Agenda Esportiva para diagnosticar e corrigir.

---

## Linha do Tempo da Conversa

### 02/02/2026 — Renato abre o problema
- Pediu ao Guilherme (suporte Agenda) que verificasse o evento Purchase no código do site
- Instrução técnica enviada: localizar `fbq('track', 'Purchase')`, verificar campo `value` e `currency`
- Regra: valor numérico > 0, sem caracteres especiais no currency

### 03/02/2026 — Guilherme responde: Purchase vai via CAPI
**Revelação crítica:** "O event purchase está sendo enviado via api de conversão, pelo token"

Ou seja: **A Agenda Esportiva JÁ TINHA CAPI configurado** — mas com bugs.

Guilherme enviou print do payload CAPI sendo enviado:
```json
{
  "event_id": "purchase_4016...",
  "event_name": "Purchase",
  "event_time": null,               ← BUG CRÍTICO: deve ser unix timestamp
  "event_source_url": "https://...=paid&utm_campaign=12024",
  "action_source": "website",
  "user_data": {...},
  "custom_data": {
    "value": 5,                      ← BUG: valor hardcoded R$5, não o preço real do ingresso
    "currency": "BRL"
  }
}
```

**Dois bugs identificados no CAPI:**
1. `event_time: null` — Meta requer unix timestamp; null provavelmente causava rejeição do evento
2. `value: 5` — Valor hardcoded como R$5 em vez do preço real (R$100, R$130, R$160+)

Guilherme diz que "está certinho seguindo a documentação do Meta" e pede confirmação do token.

### 03/02/2026 (tarde) — Token enviado e pixel ID confirmado
- Renato enviou o token Meta de acesso via WhatsApp (inseguro — token deve ser rotacionado)
- Guilherme confirma pixel ID: `2522706667879355` (correto — "Spid cup-site")
- Renato informa: "Não fazemos campanhas para os pilotos, então não tem necessidade de metrificar as inscrições de pilotos" (apenas ingressos de visitantes)
- Renato pediu URL da "página de obrigado" (última página após comprar ingresso)

### 04/02/2026 — Página de obrigado confirmada
Guilherme enviou o link:
```
https://agendaesportiva.com.br/inscricao/resumo/927745/4019210
```
**Padrão da URL de confirmação de compra:**
```
https://agendaesportiva.com.br/inscricao/resumo/{event_id}/{inscricao_id}
```

### 12/02/2026 — Renato faz follow-up
"Meta, TikTok e Google Analytics seguem sem dados de vendas, sem purchase e sem R$ gasto."

### 13/02/2026 — Guilherme: "está normal"
- "A princípio está normal amigo, todos os outros gestores de tráfego estão trabalhando normalmente"
- "Só preciso que confirme que sua Api de conversão está certinha"
- "Porque é por lá que vai o event de purchase"

### 16/02/2026 — Renato: teste servidor + descoberta na página de obrigado
**Testes realizados pelo Renato do lado do servidor Meta:** OK

**Descobertas verificando a página de obrigado:**
- **Pixel helper Meta e TikTok:** não encontraram nenhum pixel nessa página
- **Tag Manager do Google:** detectou uma tag de analytics **diferente** da configurada nas integrações da Agenda

Renato pergunta: "Em que página os eventos de purchase são enviados?"

### 18/02/2026 — Guilherme explica a arquitetura completa
**Arquitetura de eventos da Agenda Esportiva:**

| Página | Eventos disparados | Método |
|--------|-------------------|--------|
| Páginas de compra (checkout) | view_etapa, PageView, ViewContent, StartInscricao, InitiateCheckout | **Pixel browser (client-side)** |
| Página final (confirmação de pagamento) | Purchase | **Somente via CAPI (server-side)** |

**Consequência:** O pixel helper NÃO vai detectar Purchase na página de obrigado porque ele é enviado server-side — correto. O problema era outro: os bugs no payload (event_time null + value 5).

Renato faz 4 perguntas formais ao Guilherme:
1. Se houve envio de algum evento Purchase nas últimas vendas?
2. Para qual Pixel ID exatamente está sendo enviado?
3. Se o token utilizado em produção é o token atual que Renato gerou?
4. Print do log de envio de um Purchase recente (com timestamp)?

Guilherme: "Vou pedir aos desenvolvedores"

### 24/02/2026 — Follow-up, sem resposta dos devs
- Guilherme: "Cobrei o pessoal, assim que me avisarem já lhe passo"

### 26/02/2026 — Devs respondem: query do banco
Guilherme envia print de query SQL com registros:

| id_inscricao | nm_event | ds_json (início) |
|---|---|---|
| 4057549 | EndInscricao | {"events":{"ids_pixel":"2522706667879355... |
| 4057476 | EndInscricao | {"events":{"ids_pixel":"2522706667879355... |
| 4057476 | Purchase | {"events":{"ids_pixel":"2522706667879355... |
| 4057247 | EndInscricao | {"events":{"ids_pixel":"2522706667879355... |
| 4057247 | Purchase | {"events":{"ids_pixel":"2522706667879355... |
| 4057502 | EndInscricao | {"events":{"ids_pixel":"2522706667879355... |
| 4057502 | Purchase | {"events":{"ids_pixel":"2522706667879355... |
| 4057549 | Purchase | {"events":{"ids_pixel":"2522706667879355... |
| 4058284 | Purchase | {"events":{"ids_pixel":"2522706667879355... |
| 4058284 | EndInscricao | {"events":{"ids_pixel":"2522706667879355... |

**Confirmado:** Pixel ID `2522706667879355` é usado no payload. Os eventos `Purchase` e `EndInscricao` estão sendo registrados no banco da Agenda.

### 04/03/2026 — Renato: Meta voltou a funcionar
"Meta voltou a metrificar, **quarta feira da semana passada**" (~26/02/2026)

Porém: "Google Analytics e TikTok até domingo ainda não mostravam conversão e valor de vendas."

Guilherme: "bom dia, tudo certo? vou verificar"

### 15/06/2026 — Conversa migrada para Meta Business
"Esta empresa agora usa um serviço seguro da Meta para gerenciar esta conversa."  
*(Notificação automática — mudança de canal, sem resolução registrada)*

---

## Print da Página de Integrações (07/07/2026)

**Captura:** Agenda-Esportiva-07-07-2026_10_22_PM.png — SPID FEST / ID 21688

Na página de integrações do evento (aba "Integrações"), as três plataformas aparecem como **✅ Conectado**:

| Plataforma | Status na página | Dados recebidos na prática |
|-----------|-----------------|---------------------------|
| Google Analytics | ✅ Conectado | ❌ Sem purchase confirmado |
| TikTok for Business | ✅ Conectado | ❌ Sem conversões |
| Facebook | ✅ Conectado | ✅ Funcional (CAPI ativo) |

**Nota crítica:** Todas as integrações aparecem como "**Integração via Agenda Off Road**".

### Hipótese do problema Google Analytics e TikTok

A integração está ativa **na conta da Agenda Off Road**, não na conta do SPID Cup/Renato. Isso explica o achado de fevereiro: "o tag manager do Google mostrou uma tag de analytics diferente da que configurei nas integrações" — a tag que apareceu era da Agenda Off Road, não do SPID Cup.

**Ação necessária:** Verificar com Guilherme quais IDs estão configurados em cada integração:
- Google Analytics: qual Measurement ID? (G-XXXXXXXX)
- TikTok: qual Pixel ID?

Se os IDs forem da Agenda Off Road (não do SPID Cup), os dados chegam nas contas da Agenda — não nas do Renato.

---

## Diagnóstico Consolidado

### O que estava errado (fev/2026)

| Bug | Sintoma | Status |
|-----|---------|--------|
| `event_time: null` no CAPI | Purchase rejeitado ou mal atribuído pelo Meta | Resolvido ~26/02/2026 |
| `value: 5` hardcoded | ROAS e valor de venda incorretos no painel Meta | Desconhecido |
| Tag Google diferente da configuração | GA4 não recebia purchase | Sem resolução confirmada |
| Sem pixel na página de obrigado | Normal (Purchase é CAPI, não pixel) | Não era bug |

### O que é CORRETO (arquitetura da Agenda)

- **Purchase NÃO vai via pixel browser** — vai via CAPI diretamente
- Pixel browser só dispara nas páginas de checkout (InitiateCheckout, ViewContent etc.)
- Pixel ID ativo e correto: `2522706667879355`
- O pixel helper NÃO vai detectar Purchase na página de obrigado (é comportamento esperado)

### O que continua sem solução

- **Google Analytics 4:** tag diferente detectada; sem dados de purchase confirmados
- **TikTok Ads:** sem pixel instalado
- **ROAS Meta pré-correção:** os valores de compra reportados antes de ~26/02/2026 podem estar incorretos (value=5 → R$5 em vez do preço real)

---

## Contato Agenda Esportiva

- **Pessoa:** Guilherme (suporte técnico — Agenda Off Road/Esportiva)
- **Canal original:** WhatsApp pessoal
- **Atual:** Meta Business (conversa migrada 15/06/2026)
- **Responsividade:** média — costuma cobrar devs e retornar em 1–3 dias

---

## Ações para 3ª Etapa (28/08/2026)

| # | Ação | Prioridade |
|---|------|-----------|
| 1 | Verificar se `value` no CAPI agora reflete o preço real (não R$5 hardcoded) | CRÍTICA |
| 2 | Pedir print de payload Purchase recente para confirmar event_time e value corretos | ALTA |
| 3 | Perguntar ao Guilherme sobre GA4 — qual Measurement ID está configurado nas integrações? | ALTA |
| 4 | Confirmar se mudança de canal (Meta Business) mantém histórico e responsividade | MÉDIA |
| 5 | Rodar `pixel_diagnostic.py` na semana de abertura das vendas para validar eventos | ALTA |

---

## Referências

- Diagnóstico técnico atual: `~/.adforge/context/pixel_diagnostic.md`
- Gap Google/TikTok: `~/.adforge/context/gap_tracking_google_tiktok.md`
- Pixel Meta ativo: `2522706667879355` ("Spid cup-site")
- Pixel inativo (nunca disparou): `867066736318670` ("Spid Cup")
