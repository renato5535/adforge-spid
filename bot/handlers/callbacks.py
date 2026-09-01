"""Handlers para callbacks de botões inline do bot AdForge.

Formato callback_data: "{action}:{rec_id}"
Actions: aprovar, rejeitar, explicar, modificar
"""
import uuid
from datetime import datetime, timedelta, timezone
import state
import log
import llm as llm_client
from tg import make_buttons

SP_TZ = timezone(timedelta(hours=-3))

# rec_id de modificação aguardando input do usuário (in-memory)
# chave = str(chat_id), valor = rec_id
_MODIFY_AWAITING = {}


def handle_callback(ctx, callback_query):
    """Dispatcher de callbacks de botões inline."""
    cq_id      = callback_query["id"]
    data       = callback_query.get("data", "")
    msg        = callback_query.get("message", {})
    chat_id    = msg.get("chat", {}).get("id", ctx.chat_id)
    message_id = msg.get("message_id")

    if ":" not in data:
        ctx.tg.answer_callback(cq_id, "Ação desconhecida")
        return

    action, rec_id = data.split(":", 1)

    if action == "aprovar":
        _do_aprovar(ctx, cq_id, chat_id, message_id, rec_id)
    elif action == "rejeitar":
        _do_rejeitar(ctx, cq_id, chat_id, message_id, rec_id)
    elif action == "explicar":
        _do_explicar(ctx, cq_id, chat_id, rec_id)
    elif action == "modificar":
        _do_modificar(ctx, cq_id, chat_id, message_id, rec_id)
    else:
        ctx.tg.answer_callback(cq_id, "Ação '%s' não reconhecida" % action)


def _do_aprovar(ctx, cq_id, chat_id, message_id, rec_id):
    pending = state.get_pending(rec_id)
    if not pending:
        ctx.tg.answer_callback(cq_id, "Esta ação já foi processada.")
        return
    desc = pending.get("description", "ação")
    state.remove_pending(rec_id)
    state.set_last_decision({"command": "callback/aprovar", "rec_id": rec_id, "action": pending})
    ctx.tg.edit_markup(chat_id, message_id)  # remove botões
    ctx.send(
        "✅ <b>Aprovado</b>\n"
        "%s\n\n"
        "<i>Fase 1: decisão registrada em decisions.log.\n"
        "Fase 2 executará a ação via Meta API.</i>" % desc
    )
    log.log_decision("callback/aprovar", {"rec_id": rec_id}, "APROVADO: %s" % desc[:80])
    ctx.tg.answer_callback(cq_id, "✅ Aprovado!")


def _do_rejeitar(ctx, cq_id, chat_id, message_id, rec_id):
    pending = state.get_pending(rec_id)
    if not pending:
        ctx.tg.answer_callback(cq_id, "Esta ação já foi processada.")
        return
    desc = pending.get("description", "ação")
    state.remove_pending(rec_id)
    state.set_last_decision({"command": "callback/rejeitar", "rec_id": rec_id, "action": pending})
    ctx.tg.edit_markup(chat_id, message_id)  # remove botões
    ctx.send("❌ <b>Rejeitado</b>\n%s" % desc)
    log.log_decision("callback/rejeitar", {"rec_id": rec_id}, "REJEITADO: %s" % desc[:80])
    ctx.tg.answer_callback(cq_id, "❌ Rejeitado")


def _do_explicar(ctx, cq_id, chat_id, rec_id):
    ctx.tg.answer_callback(cq_id, "Consultando Claude...")
    pending = state.get_pending(rec_id)
    if not pending:
        ctx.send("⚠️ Ação não encontrada — pode já ter sido processada.")
        return
    desc = pending.get("description", "ação desconhecida")
    try:
        text, cost = llm_client.chat(
            ctx.api_key,
            [{"role": "user", "content": (
                "Contexto: campanha Meta Ads para drag racing brasileiro SPID CUP 2026.\n"
                "Explique em 3-4 linhas, com linguagem de paddock, por que esta ação é recomendada:\n"
                "\"%s\"" % desc
            )}],
            max_tokens=300,
        )
        ctx.send("💡 <b>Explicação</b>\n\n%s\n\n<i>(custo: R$ %.4f)</i>" % (text, cost))
        log.log_decision("callback/explicar", {"rec_id": rec_id}, "OK: R$%.4f" % cost)
    except llm_client.BudgetExceededError as e:
        ctx.send("⚠️ %s" % e)
        log.log_decision("callback/explicar", {"rec_id": rec_id}, "BUDGET_EXCEEDED")
    except Exception as e:
        ctx.send("❌ Erro ao consultar Claude: %s" % str(e)[:100])
        log.log_decision("callback/explicar", {"rec_id": rec_id}, "ERRO: %s" % str(e)[:60])


def _do_modificar(ctx, cq_id, chat_id, message_id, rec_id):
    ctx.tg.answer_callback(cq_id, "Ok! Descreva a modificação.")
    pending = state.get_pending(rec_id)
    if not pending:
        ctx.send("⚠️ Ação não encontrada — pode já ter sido processada.")
        return
    # Registra que estamos aguardando input para este chat
    _MODIFY_AWAITING[str(chat_id)] = rec_id
    ctx.send(
        "✏️ <b>Modificar ação</b>\n\n"
        "<b>Atual:</b> %s\n\n"
        "Como você quer modificar? Responda em texto livre." % pending.get("description", "?")
    )
    log.log_decision("callback/modificar_init", {"rec_id": rec_id}, "aguardando input do usuário")


def check_modify_response(ctx, chat_id, text):
    """
    Verifica se há fluxo de modificação aguardando para este chat.
    Retorna True se consumiu a mensagem (não deve ser roteada como comando/NL).
    """
    rec_id = _MODIFY_AWAITING.get(str(chat_id))
    if not rec_id:
        return False

    pending = state.get_pending(rec_id)
    if not pending:
        _MODIFY_AWAITING.pop(str(chat_id), None)
        return False

    _MODIFY_AWAITING.pop(str(chat_id), None)
    desc_original = pending.get("description", "?")

    try:
        prompt = (
            "Contexto: campanha Meta Ads para drag racing SPID CUP 2026.\n"
            "Ação original: \"%s\"\n"
            "Modificação solicitada pelo gestor: \"%s\"\n\n"
            "Proponha uma nova versão da ação que incorpore a modificação. "
            "Responda em 1-2 frases objetivas, como recomendação de tráfego pago."
        ) % (desc_original, text)
        new_desc, cost = llm_client.chat(
            ctx.api_key,
            [{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        # Cria novo pending com a versão modificada
        new_rec_id = str(uuid.uuid4())[:8]
        new_action = dict(pending)
        new_action["description"] = new_desc.strip()
        new_action["original_rec_id"] = rec_id
        new_action["modified_at"] = datetime.now(SP_TZ).isoformat()
        state.add_pending(new_rec_id, new_action)

        buttons = make_buttons([[
            {"text": "✅ Confirmar",  "callback_data": "aprovar:%s"  % new_rec_id},
            {"text": "❌ Cancelar",   "callback_data": "rejeitar:%s" % new_rec_id},
        ]])
        ctx.tg.send(
            ctx.chat_id,
            (
                "✏️ <b>Nova versão proposta</b>\n\n"
                "<b>Original:</b> %s\n\n"
                "<b>Modificada:</b> %s\n\n"
                "<i>(custo: R$ %.4f)</i>"
            ) % (desc_original, new_desc.strip(), cost),
            reply_markup=buttons,
        )
        log.log_decision("callback/modificar_proposta", {"novo_rec_id": new_rec_id}, "OK: R$%.4f" % cost)
    except llm_client.BudgetExceededError as e:
        ctx.send("⚠️ %s" % e)
        log.log_decision("callback/modificar", {"rec_id": rec_id}, "BUDGET_EXCEEDED")
    except Exception as e:
        ctx.send("❌ Erro ao processar modificação: %s" % str(e)[:100])
        log.log_decision("callback/modificar", {"rec_id": rec_id}, "ERRO: %s" % str(e)[:60])

    return True
