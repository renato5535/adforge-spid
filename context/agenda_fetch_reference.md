# Referência: Como Buscar Dados da Agenda Esportiva

## Método Oficial (agenda_collector.py — Playwright)

O método correto usa Playwright headless browser. Ele resolve o problema de autenticação cross-domain (cookies de `agendaesportiva.com.br` não cruzam para `api.agendaoffroad.com.br` via Python urllib).

### Fluxo de autenticação

```
1. Abrir browser headless (Chromium)
2. Navegar para AUTH_URL
3. Preencher credenciais via DOM (nm_login / nm_senha)
4. Interceptar respostas de rede durante carregamento do painel
5. Extrair token Bearer e dados da API
```

**AUTH_URL** (Next.js auth, redirecta para PHP legacy):
```
https://auth.agendaesportiva.com.br/login?legacy=true&returnTo=%2F
```

**AREA_URL** (dispara carregamento que interceptamos):
```
https://agendaesportiva.com.br/admin/controller/painel/?ref=area-do-organizador
```

### Endpoints da API

**Resumo da etapa** (requer Bearer auth):
```
GET https://api.agendaoffroad.com.br/eventoxetapa/{id}/resumo_etapa
```
Campos: `nr_pagos`, `vl_total` (líquido), `vl_inscricoes` (bruto)

**Valor de Inscrições bruto** (requer sessão PHP):
```
GET https://agendaesportiva.com.br/admin/controller/retirada_pagamento/ctrlRetirada_pagamento.php?id_eventoxetapa={id}
```
Scraping HTML: capturar "Valor de Inscrições" (sempre usar o bruto, nunca o líquido).

### Campo correto: `vl_inscricoes` (Valor de Inscrições bruto)

Usar `vl_inscricoes` da `ctrlRetirada_pagamento.php`, não `vl_total`.
`vl_total` é o valor líquido após descontos da Agenda Esportiva.

### Descoberta do ID da etapa

O `agenda_collector.py` intercepta chamadas `eventoxetapa/{id}/resumo_etapa` e filtra por:
- `TARGET_MONTH = "2026-08"` (mês corrente do evento)
- `INCLUDE_TERMS` — termos do nome do evento (ex: "spid")
- `EXCLUDE_TERMS` — termos a excluir (ex: "piloto", "no prep")

O ID da 3ª Etapa SPID Cup 2026 é descoberto dinamicamente via interceptação — não fixo em código.
Faixa esperada de IDs: ~22000–30000.

ID conhecido (sessão Ago/05/2026): **22744** (confirmado via `ctrlRetirada_pagamento.php`)

## Instalação do Playwright (se não instalado)

```powershell
pip install playwright
playwright install chromium
```

## Instabilidade Conhecida

**Sintoma:** `auth.agendaesportiva.com.br` retorna HTTP 500 intermitentemente.

**Diagnóstico rápido:**
```python
import urllib.request
r = urllib.request.urlopen("https://www.agendaesportiva.com.br/", timeout=10)
print(r.status)  # 200 = site principal OK, 500 = infra instável
```

**Quando ocorre:**
- auth.agendaesportiva.com.br → 500: servidor de autenticação instável
- www.agendaesportiva.com.br → 200: site principal funciona
- api.agendaoffroad.com.br → timeout ou 401: API travada ou token expirado

**Ação:** Aguardar recuperação (geralmente horas). O `agenda_collector.py` trata graciosamente — retorna `status: "indisponivel"` sem travar o relatório.

## Tentativas que NÃO funcionam

| Abordagem | Resultado | Motivo |
|-----------|-----------|--------|
| `urllib` com cookie jar no `auth.*` | HTTP 500 intermitente | Infra do servidor |
| `urllib` com cookie jar no PHP login | Cookies não cruzam domínio | `agendaesportiva.com.br` ≠ `api.agendaoffroad.com.br` |
| `fetch()` via JS no browser (Claude-in-Chrome) | HTML (redirect login) | Cross-domain cookies não cruzam via JS fetch |
| Ler `document.cookie` via JS | Bloqueado | Regra de segurança do session |
| Leitura direta de cookies do browser | Bloqueado por classificador | Proteção de credenciais |

## Acesso Manual (fallback)

Quando a API está instável, verificar diretamente no browser:
1. Acessar `https://agendaesportiva.com.br/admin/painel/` (já logado no Chrome)
2. Navegar até o evento SPID Cup 3ª Etapa
3. Ver "Valor de Inscrições" no painel financeiro

## Última leitura conhecida

| Data | Ingressos | Valor de Inscrições (bruto) |
|------|-----------|-----------------------------|
| 2026-08-15 | 403 | R$ 51.286,00 |
| 2026-08-17 | > 403 | > R$ 51.286,00 (Renato confirmou, leitura pendente) |

## Referência de código

- Implementação: `~/.adforge/daily_analyst/agenda_collector.py`
- Constantes-chave: `AUTH_URL`, `AREA_URL`, `API_BASE`, `RETIRADA_URL`, `TARGET_MONTH`
- Filtros de evento: `INCLUDE_TERMS`, `EXCLUDE_TERMS`
