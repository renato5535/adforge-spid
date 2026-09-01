"""Router de mensagens do AdForge Bot.

Ordem de resolução por mensagem:
  1. callback_query (botão pressionado)
  2. check_modify_response (fluxo de modificação em andamento)
  3. comando estruturado (/comando)
  4. linguagem natural → LLM (com cap R$3/dia)
"""
import os
import re
import llm as llm_client
import log
import state
from handlers import commands, callbacks

_COMMANDS = {
    "/relatorio":        commands.handle_relatorio,
    "/status":           commands.handle_status,
    "/listar_ativos":    commands.handle_listar_ativos,
    "/pausar_criativo":  commands.handle_pausar_criativo,
    "/custo_hoje":       commands.handle_custo_hoje,
    "/ajuda":            commands.handle_ajuda,
    "/start":            commands.handle_ajuda,
    "/help":             commands.handle_ajuda,
    "/desfazer_ultima":  commands.handle_desfazer_ultima,
    "/status_pendentes": commands.handle_status_pendentes,
}

# Arquivos de contexto injetados no system prompt (ordem = prioridade)
_CONTEXT_FILES = [
    "metas_2026_etapa03.md",
    "estrutura_campanha.md",
    "benchmarks_spid.md",
    "calendario_2026.md",
    "politicas_criativas.md",
    "historico_criativos.md",
]
_CONTEXT_DIR = os.path.expanduser("~/.adforge/context")
_context_cache = None  # carregado uma vez por processo


def _load_context():
    global _context_cache
    if _context_cache is not None:
        return _context_cache
    parts = []
    for fname in _CONTEXT_FILES:
        path = os.path.join(_CONTEXT_DIR, fname)
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read().strip()
            parts.append("### %s\n%s" % (fname.replace(".md", "").replace("_", " ").upper(), content))
        except Exception:
            pass
    _context_cache = "\n\n".join(parts)
    return _context_cache


_BOT_SYSTEM_BASE = (
    "Você é o assistente do AdForge, apoio ao gestor de tráfego pago Renato (SPID CUP 2026 — "
    "competições de arrancada). Responda de forma direta e consultiva, usando linguagem de paddock.\n\n"
    "REGRAS:\n"
    "- Nunca invente dados de campanha — use apenas os dados dos arquivos de contexto abaixo.\n"
    "- Quando o daily-analyst estiver pausado, diga isso claramente.\n"
    "- Você tem memória da conversa atual (histórico incluído nas mensagens).\n"
    "- Respostas curtas e objetivas. Máximo 3 parágrafos para linguagem natural.\n\n"
    "CONTEXTO DO PROJETO:\n"
    "%(context)s"
)


class BotContext:
    def __init__(self, tg, chat_id, api_key):
        self.tg      = tg
        self.chat_id = chat_id
        self.api_key = api_key

    def send(self, text, reply_markup=None):
        self.tg.send(self.chat_id, text, reply_markup=reply_markup)


def route_update(update, tg, chat_id, api_key):
    ctx = BotContext(tg, chat_id, api_key)

    # 1. Callback query (botão inline)
    if "callback_query" in update:
        callbacks.handle_callback(ctx, update["callback_query"])
        return

    # 2. Mensagem de texto
    msg  = update.get("message") or update.get("edited_message")
    if not msg:
        return
    text = (msg.get("text") or "").strip()
    if not text:
        return

    msg_chat_id = msg.get("chat", {}).get("id", chat_id)

    # 3. Fluxo de modificação em andamento?
    if callbacks.check_modify_response(ctx, msg_chat_id, text):
        return

    # 4. Comando estruturado
    m = re.match(r'^(/\w+)', text)
    if m:
        cmd = m.group(1).lower()
        if cmd == "/silenciar":
            commands.handle_silenciar(ctx, text)
            return
        if cmd == "/nova_pasta":
            commands.handle_nova_pasta(ctx, text)
            return
        if cmd == "/variacao":
            commands.handle_variacao(ctx, text)
            return
        handler = _COMMANDS.get(cmd)
        if handler:
            handler(ctx)
        else:
            ctx.send(
                "❓ Comando não reconhecido: <code>%s</code>\n"
                "Use /ajuda para ver os comandos disponíveis." % cmd
            )
        return

    # 5. Linguagem natural → LLM com contexto + histórico
    if not api_key:
        ctx.send("⚠️ ANTHROPIC_API_KEY não configurada.")
        return

    try:
        system_prompt = _BOT_SYSTEM_BASE % {"context": _load_context()}

        # Histórico + mensagem atual
        history  = state.get_history(msg_chat_id)
        messages = history + [{"role": "user", "content": text}]

        response, cost = llm_client.chat(
            api_key,
            messages,
            system=system_prompt,
            max_tokens=600,
        )

        # Persiste no histórico
        state.add_to_history(msg_chat_id, "user",      text)
        state.add_to_history(msg_chat_id, "assistant", response)

        ctx.send(response + "\n\n<i>(R$ %.4f)</i>" % cost)
        log.log_decision("llm/natural", {"query": text[:80]}, "OK: R$%.4f" % cost)
    except llm_client.BudgetExceededError as e:
        ctx.send("⚠️ " + str(e))
        log.log_decision("llm/natural", {"query": text[:80]}, "BUDGET_EXCEEDED")
    except Exception as e:
        ctx.send("❌ Erro: %s" % str(e)[:100])
        log.log_decision("llm/natural", {"query": text[:80]}, "ERRO: %s" % str(e)[:60])
