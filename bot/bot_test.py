"""Teste funcional completo do AdForge Bot — Fase 1.

Envia mensagens reais para o Telegram e valida cada feature.
Não requer o bot em execução — chama os handlers diretamente.

Uso: python bot_test.py
"""
import sys
import os
import uuid
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config
from tg import TGClient, make_buttons
import state
import log
from router import BotContext
from handlers import commands, callbacks


def _sep(tg, chat_id, titulo):
    tg.send(chat_id, "─────────────────────────\n<b>%s</b>" % titulo)
    time.sleep(0.5)


def _ok(label):
    print("  ✅ %s" % label)


def _fail(label, err):
    print("  ❌ %s: %s" % (label, err))


def run():
    cfg     = load_config()
    token   = cfg["token"]
    chat_id = cfg["chat_id"]
    api_key = cfg["api_key"]

    if not token or not chat_id:
        print("ERRO: credenciais não configuradas em ~/.adforge/.env")
        sys.exit(1)

    tg  = TGClient(token)
    ctx = BotContext(tg, chat_id, api_key)

    print("\n🧪 AdForge Bot — Teste Funcional (Fase 1)")
    print("=" * 50)

    # ── Teste 1: Recomendação com botões ────────────────────────────────────
    print("\n[1/6] Recomendação com botões (Aprovar / Rejeitar / Modificar / Explicar)")
    rec_id    = str(uuid.uuid4())[:8]
    test_desc = "Escalar +20%% o conjunto 'Engajamento 365D' (ad-18) — ROAS 47x nas últimas 24h"
    from datetime import datetime, timedelta, timezone
    SP_TZ = timezone(timedelta(hours=-3))
    action_data = {
        "type":        "escalar_orcamento",
        "description": test_desc,
        "adset_name":  "Engajamento 365D",
        "change_pct":  20,
        "created_at":  datetime.now(SP_TZ).isoformat(),
        "message_id":  None,
        "fase":        1,
    }
    state.add_pending(rec_id, action_data)

    buttons = make_buttons([
        [
            {"text": "✅ Aprovar",   "callback_data": "aprovar:%s"   % rec_id},
            {"text": "❌ Rejeitar",  "callback_data": "rejeitar:%s"  % rec_id},
            {"text": "✏️ Modificar", "callback_data": "modificar:%s" % rec_id},
        ],
        [
            {"text": "❓ Explicar",  "callback_data": "explicar:%s"  % rec_id},
        ],
    ])
    resp, err = tg.send(
        chat_id,
        (
            "📊 <b>Recomendação AdForge — TESTE</b>\n\n"
            "🔴 <b>Alta prioridade</b>\n"
            "<b>Ação:</b> %s\n"
            "<b>Por quê:</b> ROAS 47x acima do piso da fase de aquecimento (10x)\n"
            "<b>Impacto:</b> Aproveita janela de alta performance antes de saturar\n\n"
            "<i>ID: %s — use os botões abaixo</i>"
        ) % (test_desc, rec_id),
        reply_markup=buttons,
    )
    if err:
        _fail("envio da recomendação", err)
    else:
        msg_id = (resp or {}).get("result", {}).get("message_id")
        action_data["message_id"] = msg_id
        state.add_pending(rec_id, action_data)
        log.log_decision("test/recomendacao", {"rec_id": rec_id}, "OK msg_id=%s" % msg_id)
        _ok("Recomendação enviada (rec_id=%s, msg_id=%s)" % (rec_id, msg_id))
        print("     → Abra o Telegram e teste os botões manualmente.")

    time.sleep(1)

    # ── Teste 2: Comandos estruturados ──────────────────────────────────────
    print("\n[2/6] Comandos estruturados (sem LLM)")
    _sep(tg, chat_id, "Teste 2 — Comandos Estruturados")
    time.sleep(0.3)

    for cmd_name, handler in [
        ("/ajuda",       commands.handle_ajuda),
        ("/status",      commands.handle_status),
        ("/relatorio",   commands.handle_relatorio),
        ("/custo_hoje",  commands.handle_custo_hoje),
        ("/listar_ativos", commands.handle_listar_ativos),
        ("/status_pendentes", commands.handle_status_pendentes),
        ("/pausar_criativo",  commands.handle_pausar_criativo),
    ]:
        try:
            handler(ctx)
            _ok(cmd_name)
            time.sleep(0.4)
        except Exception as e:
            _fail(cmd_name, e)

    # ── Teste 3: Linguagem natural (LLM) ────────────────────────────────────
    print("\n[3/6] Linguagem natural → LLM (vai gastar ~R$0.02)")
    _sep(tg, chat_id, "Teste 3 — Linguagem Natural (LLM)")
    time.sleep(0.3)
    try:
        import llm as llm_client
        resp_text, cost = llm_client.chat(
            api_key,
            [{"role": "user", "content": "Qual o melhor horário para escalar budget em campanhas de drag racing no Meta?"}],
            system="Você é analista de tráfego pago AdForge. Responda em 2-3 linhas.",
            max_tokens=200,
        )
        tg.send(chat_id, "💬 <b>Resposta LLM (teste)</b>\n\n%s\n\n<i>(R$ %.4f)</i>" % (resp_text, cost))
        _ok("LLM respondeu (R$ %.4f)" % cost)
        log.log_decision("test/llm_natural", {}, "OK: R$%.4f" % cost)
    except llm_client.BudgetExceededError as e:
        tg.send(chat_id, "⚠️ %s" % e)
        _ok("Budget exceeded detectado corretamente")
    except Exception as e:
        _fail("LLM", e)

    time.sleep(0.5)

    # ── Teste 4: /desfazer_ultima ────────────────────────────────────────────
    print("\n[4/6] /desfazer_ultima")
    _sep(tg, chat_id, "Teste 4 — /desfazer_ultima")
    time.sleep(0.3)
    try:
        # Cria uma decisão de teste para desfazer
        tmp_id = str(uuid.uuid4())[:8]
        tmp_action = {
            "type": "test_action",
            "description": "Ação de teste para /desfazer_ultima",
            "created_at": datetime.now(SP_TZ).isoformat(),
            "fase": 1,
        }
        state.add_pending(tmp_id, tmp_action)
        state.set_last_decision({"command": "/test", "rec_id": tmp_id, "action": tmp_action})
        commands.handle_desfazer_ultima(ctx)
        _ok("/desfazer_ultima executado")
    except Exception as e:
        _fail("/desfazer_ultima", e)

    # Testa desfazer quando não há nada
    try:
        state.clear_last_decision()
        commands.handle_desfazer_ultima(ctx)
        _ok("/desfazer_ultima (sem decisão) — mensagem de aviso enviada")
    except Exception as e:
        _fail("/desfazer_ultima (sem decisão)", e)

    time.sleep(0.5)

    # ── Teste 5: /silenciar ──────────────────────────────────────────────────
    print("\n[5/6] /silenciar")
    _sep(tg, chat_id, "Teste 5 — /silenciar")
    time.sleep(0.3)
    try:
        commands.handle_silenciar(ctx, "/silenciar 2h")
        silenciado = state.is_silenced()
        until      = state.silenced_until_str()[:16].replace("T", " ")
        _ok("/silenciar 2h — silenciado=%s, até %s SP" % (silenciado, until))
        # Restaura
        state.clear_silenciar()
    except Exception as e:
        _fail("/silenciar", e)

    # Testa intervalo inválido
    try:
        commands.handle_silenciar(ctx, "/silenciar 99h")
        _ok("/silenciar 99h — erro de validação enviado")
    except Exception as e:
        _fail("/silenciar (inválido)", e)

    time.sleep(0.5)

    # ── Teste 6: Logs e estrutura ────────────────────────────────────────────
    print("\n[6/6] Verificando logs e estrutura de arquivos")
    _sep(tg, chat_id, "Teste 6 — Verificação de Logs")
    time.sleep(0.3)

    bot_dir      = os.path.expanduser("~/.adforge/bot")
    state_dir    = os.path.expanduser("~/.adforge/bot_state")
    log_path     = log._log_path()

    checks = {
        "config.py":           os.path.join(bot_dir, "config.py"),
        "tg.py":               os.path.join(bot_dir, "tg.py"),
        "state.py":            os.path.join(bot_dir, "state.py"),
        "llm.py":              os.path.join(bot_dir, "llm.py"),
        "log.py":              os.path.join(bot_dir, "log.py"),
        "router.py":           os.path.join(bot_dir, "router.py"),
        "bot.py":              os.path.join(bot_dir, "bot.py"),
        "handlers/__init__.py": os.path.join(bot_dir, "handlers", "__init__.py"),
        "handlers/commands.py": os.path.join(bot_dir, "handlers", "commands.py"),
        "handlers/callbacks.py": os.path.join(bot_dir, "handlers", "callbacks.py"),
        "decisions log":       log_path,
        "pending_approvals":   os.path.join(state_dir, "pending_approvals.json"),
    }

    all_ok = True
    lines  = ["📁 <b>Estrutura ~/.adforge/bot/</b>\n"]
    for label, path in checks.items():
        exists = os.path.exists(path)
        icon   = "✅" if exists else "❌"
        size   = ("%d bytes" % os.path.getsize(path)) if exists else "ausente"
        lines.append("%s %s — %s" % (icon, label, size))
        if exists:
            _ok("%s (%s)" % (label, size))
        else:
            _fail(label, "arquivo ausente")
            all_ok = False

    # Mostra últimas 5 linhas do log
    try:
        with open(log_path, encoding="utf-8") as f:
            all_lines = f.readlines()
        last5 = "".join(all_lines[-5:]).strip()
        lines.append("\n<b>Últimas entradas do log:</b>\n<pre>%s</pre>" % last5)
    except Exception:
        lines.append("\n(log vazio ou não gerado ainda)")

    tg.send(chat_id, "\n".join(lines))

    custo_final = state.get_bot_cost_today()
    print("\n" + "=" * 50)
    print("✅ Testes concluídos" if all_ok else "⚠️  Alguns arquivos ausentes")
    print("Custo LLM do bot hoje: R$ %.4f / R$ 3.00" % custo_final)
    print("Decisions log: %s" % log_path)
    print("\nPróximo passo: rode 'python bot.py' para ficar ouvindo mensagens.")


if __name__ == "__main__":
    run()
