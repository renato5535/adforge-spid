"""Handlers para comandos estruturados do bot AdForge.

Nenhum desses handlers chama LLM — todos são determinísticos e gratuitos.
"""
import os
import re
import json
import uuid
import sys
from datetime import datetime, timedelta, timezone
import state
import log

# Adiciona raiz do .adforge ao path para imports cross-module
_adforge_root = os.path.expanduser("~/.adforge")
if _adforge_root not in sys.path:
    sys.path.insert(0, _adforge_root)

SP_TZ   = timezone(timedelta(hours=-3))
_REPORTS = os.path.expanduser("~/.adforge/reports")
_LOGS    = os.path.expanduser("~/.adforge/logs")


def handle_relatorio(ctx):
    """Envia o último relatório diário salvo."""
    try:
        files = sorted(
            [f for f in os.listdir(_REPORTS)
             if len(f) == 13 and f.endswith(".md")],  # YYYY-MM-DD.md
            reverse=True,
        )
        if not files:
            ctx.send("Nenhum relatório encontrado. O daily-analyst está pausado.")
            log.log_decision("/relatorio", {}, "sem relatórios")
            return
        path = os.path.join(_REPORTS, files[0])
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if len(content) > 3800:
            content = content[:3800] + "\n\n[...relatório truncado — use /relatorio no app]"
        ctx.send(content)
        log.log_decision("/relatorio", {"arquivo": files[0]}, "OK")
    except Exception as e:
        ctx.send("Erro ao carregar relatório: %s" % e)
        log.log_decision("/relatorio", {}, "ERRO: %s" % e)


def handle_status(ctx):
    """Mostra status da última execução do daily-analyst."""
    try:
        with open(os.path.join(_LOGS, "last_run.json"), encoding="utf-8") as f:
            d = json.load(f)
        ts     = d.get("finished_at", "?")[:19].replace("T", " ")
        agenda = d.get("agenda_status", "?")
        tg_ok  = "✅" if (d.get("telegram") or {}).get("ok") else "❌"
        llm    = d.get("guardrails", {}).get("llm_brl", 0)
        src    = d.get("recs_source", "?")
        msg = (
            "📊 <b>Status AdForge</b>\n\n"
            "Última execução: <code>%s</code>\n"
            "Agenda: %s\n"
            "Telegram: %s\n"
            "Custo LLM (daily-analyst): R$ %.4f\n"
            "Fonte recomendações: %s\n\n"
            "<i>Daily-analyst pausado. Reativar quando campanha subir (24/Jul).</i>"
        ) % (ts, agenda, tg_ok, float(llm), src)
        ctx.send(msg)
        log.log_decision("/status", {}, "OK")
    except Exception as e:
        ctx.send(
            "⚠️ Sem dados de execução disponíveis.\n"
            "Daily-analyst está pausado (sem campanha ativa).\n\n"
            "<code>%s</code>" % e
        )
        log.log_decision("/status", {}, "sem dados: %s" % e)


def handle_listar_ativos(ctx):
    """Fase 1: informa que lista de criativos requer execução do daily-analyst."""
    ctx.send(
        "📋 <b>Criativos Ativos</b>\n\n"
        "Daily-analyst pausado — dados em tempo real indisponíveis.\n\n"
        "Para ver criativos ativos:\n"
        "• Acesse o Gerenciador de Anúncios Meta\n"
        "• Ou reative o scheduler: <code>Enable-ScheduledTask -TaskName 'DailyAnalyst' -TaskPath '\\AdForge\\'</code>\n\n"
        "Quando a campanha da 3ª Etapa subir (24/Jul), esta lista virá do relatório automático."
    )
    log.log_decision("/listar_ativos", {}, "info estática (scheduler pausado)")


def handle_pausar_criativo(ctx):
    """Fase 1: registra intenção de pausa sem executar via API."""
    rec_id = str(uuid.uuid4())[:8]
    now_iso = datetime.now(SP_TZ).isoformat()
    action_data = {
        "type": "pausar_criativo",
        "description": "Pausa de criativo (via /pausar_criativo — especificar nome/ID)",
        "created_at": now_iso,
        "message_id": None,
        "fase": 1,
    }
    state.add_pending(rec_id, action_data)
    state.set_last_decision({"command": "/pausar_criativo", "rec_id": rec_id, "action": action_data})
    ctx.send(
        "⚠️ <b>Fase 1 — Intenção registrada</b>\n\n"
        "ID: <code>%s</code>\n"
        "Ação: Pausa de criativo\n\n"
        "Execução real via API (Fase 2) ainda não implementada.\n"
        "Para pausar agora: acesse o Gerenciador Meta.\n\n"
        "✅ Registrado em decisions.log e pending_approvals.json\n"
        "Use /desfazer_ultima para cancelar." % rec_id
    )
    log.log_decision("/pausar_criativo", {"rec_id": rec_id}, "REGISTRADO (Fase 1)")


def handle_custo_hoje(ctx):
    """Mostra custo LLM do bot hoje (cap R$3) e lembra do daily-analyst."""
    custo_bot = state.get_bot_cost_today()
    disponivel = max(0.0, 3.0 - custo_bot)
    msg = (
        "💰 <b>Custo LLM — Hoje</b>\n\n"
        "<b>Bot</b> (cap R$3/dia)\n"
        "  Gasto: R$ %.4f\n"
        "  Disponível: R$ %.4f\n\n"
        "<b>Daily Analyst</b> (cap R$10/dia)\n"
        "  Pausado — sem custo hoje\n\n"
        "<i>Caps são independentes e reiniciam à meia-noite SP.</i>"
    ) % (custo_bot, disponivel)
    ctx.send(msg)
    log.log_decision("/custo_hoje", {}, "bot=R$%.4f" % custo_bot)


def handle_ajuda(ctx):
    msg = (
        "🤖 <b>AdForge Bot</b>\n\n"
        "<b>Relatórios</b>\n"
        "/relatorio — último relatório diário\n"
        "/status — status da última execução\n\n"
        "<b>Drive → Meta</b>\n"
        "/nova_pasta URL_OU_ID [adset_id] — enfileira pasta do Drive para criação de ads\n\n"
        "<b>Criativos</b>\n"
        "/listar_ativos — criativos ativos\n"
        "/pausar_criativo — registrar intenção de pausa\n\n"
        "<b>Aprovações</b>\n"
        "/status_pendentes — aprovações aguardando\n"
        "/desfazer_ultima — reverte última decisão\n\n"
        "<b>Notificações</b>\n"
        "/silenciar 2h — pausa notificações (1h–24h)\n"
        "/custo_hoje — custo LLM do bot hoje\n\n"
        "<b>Criativos — IA</b>\n"
        "/variacao [briefing] → 3 bodies + 3 headlines via OpenRouter\n"
        "(R$5/dia de budget separado)\n\n"
        "<b>Linguagem natural</b>\n"
        "Texto livre → resposta consultiva via Claude\n"
        "(R$3/dia de budget separado)"
    )
    ctx.send(msg)
    log.log_decision("/ajuda", {}, "OK")


def handle_desfazer_ultima(ctx):
    """Reverte a última decisão registrada."""
    last = state.get_last_decision()
    if not last:
        ctx.send("⚠️ Nenhuma decisão recente para desfazer.")
        log.log_decision("/desfazer_ultima", {}, "nada para desfazer")
        return

    cmd     = last.get("command", "?")
    rec_id  = last.get("rec_id", "")
    desc    = (last.get("action") or {}).get("description", "?")

    if rec_id:
        removed = state.remove_pending(rec_id)
        state.clear_last_decision()
        if removed:
            ctx.send(
                "↩️ <b>Decisão desfeita</b>\n\n"
                "Comando: %s\n"
                "ID: <code>%s</code>\n"
                "Ação: %s\n\n"
                "✅ Removido de pending_approvals e registrado em decisions.log." % (cmd, rec_id, desc)
            )
            log.log_decision("/desfazer_ultima", {"cmd": cmd, "rec_id": rec_id}, "DESFEITO")
            return

    # Decisão já processada (ex: aprovação confirmada)
    ctx.send(
        "↩️ <b>Última decisão registrada</b>\n\n"
        "Comando: %s\n"
        "Ação: %s\n\n"
        "⚠️ Decisão já foi processada — não é possível desfazer via Fase 1.\n"
        "Fase 2 permitirá reversão de ações executadas via API." % (cmd, desc)
    )
    log.log_decision("/desfazer_ultima", {"cmd": cmd}, "já processada — sem reversão")
    state.clear_last_decision()


def handle_status_pendentes(ctx):
    """Lista todas as aprovações aguardando resposta."""
    pending = state.list_pending()
    if not pending:
        ctx.send("✅ Nenhuma aprovação pendente no momento.")
        log.log_decision("/status_pendentes", {}, "0 pendentes")
        return

    lines = ["📋 <b>Aprovações Pendentes (%d)</b>\n" % len(pending)]
    for rec_id, data in pending.items():
        desc    = data.get("description", "sem descrição")
        criado  = data.get("created_at", "?")[:16].replace("T", " ")
        tipo    = data.get("type", "?")
        lines.append(
            "• <code>%s</code> [%s]\n  %s\n  Criado: %s" % (rec_id, tipo, desc, criado)
        )
    ctx.send("\n\n".join(lines))
    log.log_decision("/status_pendentes", {}, "%d pendentes" % len(pending))


def handle_nova_pasta(ctx, text):
    """
    Registra uma pasta do Google Drive na fila para processamento.

    Uso: /nova_pasta FOLDER_ID_OU_URL [adset_id] [label]
    Exemplos:
      /nova_pasta 1ZRuRyOEW2FmclVT2L_XXNqSBj37pnLmz
      /nova_pasta https://drive.google.com/drive/folders/1ZRuRy... 23989229 "3ª Etapa artes"
    """
    from drive_actions.drive_queue import add_folder, extract_folder_id

    # Extrai argumentos: /nova_pasta URL_OU_ID [adset_id] ["label"]
    parts = text.strip().split(None, 3)
    # parts[0] = /nova_pasta, parts[1] = URL/ID, parts[2] = adset_id?, parts[3] = label?
    if len(parts) < 2:
        ctx.send(
            "❌ Uso: <code>/nova_pasta FOLDER_ID_OU_URL [adset_id] [label]</code>\n\n"
            "Exemplos:\n"
            "<code>/nova_pasta 1ZRuRyOEW2...</code>\n"
            "<code>/nova_pasta https://drive.google.com/drive/folders/1ZRuRy... 23989229</code>"
        )
        return

    raw_id  = parts[1]
    adset   = parts[2] if len(parts) > 2 else ""
    label   = parts[3].strip('"\'') if len(parts) > 3 else ""

    # Limpa adset_id: remove se parecer um URL ou não for numérico
    if adset and (adset.startswith("http") or not adset.replace("_", "").isdigit()):
        label = adset  # provavelmente pulou o adset_id
        adset = ""

    folder_id = extract_folder_id(raw_id)
    if not folder_id or len(folder_id) < 10:
        ctx.send("❌ Não consegui extrair um folder_id válido de: <code>%s</code>" % raw_id[:80])
        return

    item = add_folder(folder_id, label=label or "SPID Drive", adset_id=adset)

    adset_info = ("adset: <code>%s</code>" % adset) if adset else "adset: ⚠️ <b>não informado</b>"
    ctx.send(
        "📂 <b>Pasta na fila de processamento</b>\n\n"
        "ID Drive: <code>%s</code>\n"
        "Label: %s\n"
        "%s\n\n"
        "✅ Salvo em <code>drive_queue.json</code>\n\n"
        "📌 Próximo passo: <b>abra uma sessão no Claude</b> para eu processar a pasta.\n"
        "Vou baixar as imagens do Drive e criar os ads no Meta (pausados).\n"
        "Você aprova cada ad antes de ativar.\n\n"
        "<i>Se quiser informar o adset_id depois:\n"
        "<code>/nova_pasta %s SEU_ADSET_ID</code></i>"
        % (folder_id, item["label"], adset_info, folder_id)
    )
    log.log_decision("/nova_pasta", {"folder_id": folder_id, "adset": adset, "label": label}, "ENFILEIRADO")


def handle_variacao(ctx, text):
    """
    Gera variações de copy via OpenRouter (gpt-4o-mini).

    Uso: /variacao [briefing do criativo]
    Ex:  /variacao familia 3 lote R$135, publico frio, urgencia 15 dias
    """
    import sys, os
    sys.path.insert(0, os.path.expanduser("~/.adforge/bot"))
    import llm_openrouter as or_client
    from daily_analyst.common import load_env as _load_env  # noqa

    # Extrai briefing (tudo após /variacao)
    parts = text.strip().split(None, 1)
    briefing = parts[1].strip() if len(parts) > 1 else ""

    if not briefing:
        ctx.send(
            "❌ Informe o briefing após o comando.\n\n"
            "Exemplos:\n"
            "<code>/variacao família 3º lote R$135, público frio, urgência 15 dias</code>\n"
            "<code>/variacao individual R$80, RMKT, gancho de volta pra pista</code>\n"
            "<code>/variacao pilotos confirmados, gerar curiosidade, sexta R$40</code>"
        )
        return

    ctx.send("✍️ Gerando variações via OpenRouter...")

    try:
        adforge_root = os.path.expanduser("~/.adforge")
        sys.path.insert(0, os.path.join(adforge_root, "daily_analyst"))
        from common import load_env
        env    = load_env()
        or_key = env.get("OPENROUTER_API_KEY", "")
        if not or_key:
            ctx.send("⚠️ OPENROUTER_API_KEY não configurada no .env")
            return

        resultado, custo = or_client.gerar_variacao(or_key, briefing)

        ctx.send(
            "🎨 <b>Variações de Copy — SPID Cup</b>\n"
            "<i>Briefing: %s</i>\n\n"
            "%s\n\n"
            "<i>Modelo: gpt-4o-mini | Custo: R$ %.4f</i>" % (briefing[:80], resultado, custo)
        )
        log.log_decision("/variacao", {"briefing": briefing[:80]}, "OK: R$%.4f" % custo)

    except or_client.BudgetExceededError as e:
        ctx.send("⚠️ %s" % e)
        log.log_decision("/variacao", {"briefing": briefing[:60]}, "BUDGET_EXCEEDED")
    except Exception as e:
        ctx.send("❌ Erro ao gerar variações: %s" % str(e)[:120])
        log.log_decision("/variacao", {"briefing": briefing[:60]}, "ERRO: %s" % str(e)[:60])


def handle_silenciar(ctx, text):
    """Pausa notificações proativas por X horas (1–24h)."""
    m = re.search(r'/silenciar\s+(\d+)\s*h?', text, re.IGNORECASE)
    if not m:
        ctx.send("❌ Uso: <code>/silenciar 2h</code>  (aceita 1h a 24h)")
        return
    hours = int(m.group(1))
    if not (1 <= hours <= 24):
        ctx.send("❌ Intervalo inválido. Use entre 1h e 24h.")
        return
    state.set_silenciar(hours)
    until = (datetime.now(SP_TZ) + timedelta(hours=hours)).strftime("%H:%M")
    ctx.send(
        "🔇 <b>Notificações pausadas</b>\n\n"
        "Silenciado por %dh (até %s, horário SP).\n\n"
        "Comandos continuam funcionando normalmente.\n"
        "Para reativar antes do prazo: <code>/silenciar 0h</code> não funciona — "
        "reinicie o bot ou aguarde o prazo." % (hours, until)
    )
    log.log_decision("/silenciar", {"hours": hours}, "até %s SP" % until)
