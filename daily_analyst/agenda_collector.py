"""Passo B — Coleta Agenda Esportiva via login + interceptação dinâmica.

Flow:
  1. Login via auth.agendaesportiva.com.br
  2. Navega para o painel — intercept TODAS as chamadas resumo_etapa
  3. Para cada ID capturado, consulta /eventoxetapa/{id} para obter nome e data
  4. Seleciona o evento que corresponde ao TARGET_MONTH (visitantes, não pilotos)
  5. Acessa ctrlRetirada_pagamento.php com o ID descoberto
  6. Retorna nr_pagos, nr_reservados, vl_total, vl_inscricoes

Se o evento do mês-alvo não existir na Agenda Esportiva ainda, retorna
status 'evento_nao_cadastrado' com mensagem clara — nunca dados de evento errado.

SOMENTE LEITURA.
"""
import os
import re
import json
from common import brl, now_sp, SHOTS_DIR

# Mês-alvo: "YYYY-MM" — ajustar quando trocar de etapa
TARGET_MONTH   = "2026-08"
# Palavras que DEVEM aparecer no nome da etapa (ao menos 1)
INCLUDE_TERMS  = ["visitant", "ingresso", "ingressos", "etapa 3", "3a etapa", "3ª etapa"]
# Palavras que EXCLUEM o evento (evitar pilotos e eventos de NO PREP / festival)
EXCLUDE_TERMS  = ["piloto", "pilotos", "no prep", "noprep", "festival"]

AUTH_URL     = "https://auth.agendaesportiva.com.br/login?legacy=true&returnTo=%2F"
AREA_URL     = "https://agendaesportiva.com.br/admin/controller/painel/?ref=area-do-organizador"
API_BASE     = "https://api.agendaoffroad.com.br"
RETIRADA_URL = ("https://agendaesportiva.com.br/admin/controller/retirada_pagamento/"
                "ctrlRetirada_pagamento.php?id_eventoxetapa=")


def _parse_vl_inscricoes(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    m = re.search(r'Valor de Inscri\S+\s+R\$\s*([\d.,]+)', text)
    if not m:
        return None
    try:
        return float(m.group(1).replace('.', '').replace(',', '.'))
    except Exception:
        return None


def _unavailable(motivo):
    return {"status": "indisponivel", "motivo": motivo, "screenshot": None}


def _not_registered():
    return {
        "status": "evento_nao_cadastrado",
        "motivo": "3ª Etapa SPID Cup 2026 (agosto/%s) ainda não encontrada na Agenda Esportiva" % TARGET_MONTH,
        "screenshot": None,
    }


def _is_target_event(info):
    """Retorna True se o evento corresponde à etapa-alvo (mês correto, visitantes, não pilotos)."""
    nm  = (info.get("nm_etapa") or "").lower()
    dt  = (info.get("dt_etapa") or "")[:7]   # "YYYY-MM"

    if dt != TARGET_MONTH:
        return False
    for term in EXCLUDE_TERMS:
        if term in nm:
            return False
    for term in INCLUDE_TERMS:
        if term in nm:
            return True
    # Se a data bate e não é pilotos, aceitar como candidato (evento novo com nome diferente)
    return True


def collect(env, g, timeout_ms=90000):
    if not g.time_ok():
        return _unavailable("guardrail de tempo atingido antes do Agenda")

    email = env.get("AGENDA_ESPORTIVA_EMAIL", "").strip()
    pwd   = env.get("AGENDA_ESPORTIVA_PASSWORD", "").strip()
    if not email or not pwd:
        return _unavailable("credenciais do Agenda ausentes no .env")

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return _unavailable("Playwright nao instalado (pip install playwright; playwright install chromium)")

    os.makedirs(SHOTS_DIR, exist_ok=True)
    shot = os.path.join(SHOTS_DIR, "%s-agenda.png" % now_sp().strftime("%Y-%m-%d"))

    # Dicionário: {etapa_id: dados_resumo}
    captured = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx     = browser.new_context()
            page    = ctx.new_page()
            page.set_default_timeout(timeout_ms)

            # Interceptar TODAS as respostas resumo_etapa
            def on_response(response):
                m = re.search(r"eventoxetapa/(\d+)/resumo_etapa", response.url)
                if m:
                    etapa_id = m.group(1)
                    if etapa_id not in captured:
                        try:
                            captured[etapa_id] = response.json()
                        except Exception:
                            captured[etapa_id] = {}

            page.on("response", on_response)

            # 1. Login
            page.goto(AUTH_URL)
            page.wait_for_load_state("networkidle")
            page.fill('input[name="nm_login"]', email)
            page.fill('input[name="nm_senha"]', pwd)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

            # 2. Carregar painel — dispara chamadas automáticas de resumo_etapa
            # Usa domcontentloaded para não travar no networkidle; JS dispara depois.
            try:
                page.goto(AREA_URL, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass
            # Aguarda estabilização antes de ler conteúdo (evita "page is navigating")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(3000)

            # Detecta tela intermediária "Tudo certo por aqui!" (aparece após login
            # quando o site redireciona para área de participantes antes do painel).
            # Sem clicar em botões — cliques criam conflito com goto subsequente.
            try:
                _html = page.content().lower()
            except Exception:
                _html = ""
            if "tudo certo" in _html or "ver todos os eventos" in _html:
                page.wait_for_timeout(1500)
                try:
                    page.goto(AREA_URL, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    pass
                page.wait_for_timeout(3000)
                # Scroll para disparar lazy-loads do painel
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                except Exception:
                    pass
                page.wait_for_timeout(1000)

            # Aguarda até 10s por pelo menos 1 resumo_etapa; retry se vazio
            for _wait in (3000, 3000, 4000):
                page.wait_for_timeout(_wait)
                if captured:
                    break

            # Último recurso: recarrega AREA_URL e tenta mais uma vez
            if not captured:
                try:
                    page.goto(AREA_URL, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    pass
                for _wait in (3000, 3000, 4000):
                    page.wait_for_timeout(_wait)
                    if captured:
                        break

            page.screenshot(path=shot, full_page=False)

            if not captured:
                browser.close()
                return _unavailable("nenhuma chamada resumo_etapa capturada no painel")

            # 3. Para cada ID capturado, buscar metadados via API
            target_id   = None
            target_data = None

            candidates = []
            for etapa_id, resumo in captured.items():
                try:
                    resp = page.request.get(
                        "%s/eventoxetapa/%s" % (API_BASE, etapa_id),
                        timeout=15000,
                    )
                    info = resp.json() if resp.ok else {}
                except Exception:
                    info = {}

                if _is_target_event(info):
                    candidates.append((etapa_id, resumo, info))

            if not candidates:
                browser.close()
                return _not_registered()

            # Preferir evento com "visitant" ou "ingresso" no nome; desempate: maior nr_pagos
            def _score(c):
                nm = (c[2].get("nm_etapa") or "").lower()
                priority = 1 if any(t in nm for t in ["visitant", "ingresso", "ingressos"]) else 0
                nr_pagos = c[1].get("nr_pagos") or 0
                return (priority, nr_pagos)

            candidates.sort(key=_score, reverse=True)
            target_id, target_data, target_info = candidates[0]

            # 4. Buscar Valor de Inscrições via ctrlRetirada_pagamento
            vl_inscricoes = None
            try:
                page.goto(RETIRADA_URL + target_id)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                vl_inscricoes = _parse_vl_inscricoes(page.content())
            except Exception:
                pass

            browser.close()

        nr_pagos      = target_data.get("nr_pagos")
        nr_reservados = target_data.get("nr_reservados")
        vl_total      = target_data.get("vl_total")
        nm_etapa      = target_info.get("nm_etapa") or target_info.get("nome") or ("ID " + target_id)

        status = "ok" if nr_pagos is not None else "parcial"
        return {
            "status":        status,
            "motivo":        None,
            "screenshot":    shot,
            "evento_id":     target_id,
            "evento_nome":   nm_etapa,
            "total_vendido": nr_pagos,
            "reservados":    nr_reservados,
            "vl_inscricoes": vl_inscricoes,
            "faturamento":   brl(vl_inscricoes) if vl_inscricoes is not None else brl(vl_total),
            "vl_total":      vl_total,
        }

    except Exception as e:
        return _unavailable("falha geral: %s" % str(e)[:160])
