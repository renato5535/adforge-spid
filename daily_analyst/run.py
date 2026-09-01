#!/usr/bin/env python3
"""@daily-analyst — orquestrador do loop agêntico (somente leitura).

Fluxo (ETAPA 2): Coleta Meta -> Coleta Agenda -> Análise -> Recomendações ->
Relatório markdown -> Entrega Telegram. Encerra ao enviar com sucesso OU ao
atingir qualquer guardrail (tempo, chamadas API, budget LLM).

Uso:
  python run.py                # execução completa (coleta + relatório + Telegram)
  python run.py --no-telegram  # tudo menos o envio (teste local)
"""
import os
import sys
import json
import traceback
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import load_env, load_context_files, now_sp, REPORTS_DIR, LOGS_DIR  # noqa: E402
from guardrails import Guardrails  # noqa: E402
import meta_collector
import agenda_collector
import analyzer
import recommender
import report
import telegram_send

EVENT_DATE = date(2026, 8, 28)  # 3ª Etapa SPID CUP 2026


def log(msg):
    line = "[%s] %s" % (now_sp().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(os.path.join(LOGS_DIR, "run-%s.log" % now_sp().strftime("%Y-%m-%d")),
                  "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as _e:
        sys.stderr.write("LOG-WRITE-ERR: %s\n" % _e)


def main():
    no_tg = "--no-telegram" in sys.argv
    env = load_env()
    context = load_context_files()
    g = Guardrails(
        max_api_calls=env.get("MAX_API_CALLS_PER_EXECUTION", 50),
        max_minutes=env.get("MAX_EXECUTION_MINUTES", 15),
        max_llm_brl=env.get("MAX_LLM_BUDGET_BRL", 10),
    )
    dias = (EVENT_DATE - now_sp().date()).days

    log("=== @daily-analyst START === (caps: %s calls / %s min / R$%s LLM)" % (
        g.max_api_calls, g.max_seconds // 60, g.max_llm_brl))

    # Passo A — Meta
    try:
        meta = meta_collector.collect(env, g)
        log("Meta: %d campanhas, %d conjuntos, %d anúncios | %d chamadas API | erros: %d" % (
            len(meta["campaigns"]), len(meta["adsets"]), len(meta["ads"]),
            g.api_calls, len(meta["errors"])))
    except Exception as e:
        log("Meta FALHOU: %s" % e)
        meta = {"campaigns": [], "adsets": [], "ads": [], "totals": {}, "errors": [str(e)], "zero_delivery": []}

    # Passo B — Agenda (gracioso)
    try:
        agenda = agenda_collector.collect(env, g)
        log("Agenda: status=%s (%s)" % (agenda.get("status"), agenda.get("motivo") or "ok"))
    except Exception as e:
        agenda = {"status": "indisponivel", "motivo": str(e)[:120], "screenshot": None}
        log("Agenda FALHOU: %s" % e)

    # Passo C — Análise
    analysis = analyzer.analyze(meta, agenda, dias)
    log("Análise: %d alertas | top=%d bottom=%d | zero-delivery=%d" % (
        len(analysis["alertas"]), len(analysis["top3"]), len(analysis["bottom3"]),
        analysis["n_zero_delivery"]))

    # Passo D — Recomendações (híbrido)
    recs, recs_source = recommender.recommend(env, meta, analysis, g, context=context, dias=dias)
    log("Recomendações: %d (%s)" % (len(recs), recs_source))

    # Passo E — Relatório
    gm = g.metrics()
    md = report.build(meta, agenda, analysis, recs, recs_source, gm)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    rpath = os.path.join(REPORTS_DIR, "%s.md" % now_sp().strftime("%Y-%m-%d"))
    with open(rpath, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    log("Relatório salvo: %s (%d chars)" % (rpath, len(md)))

    # Passo F — Telegram
    tg = {"ok": None, "skipped": no_tg}
    if not no_tg:
        summary = report.summary_for_telegram(meta, agenda, analysis, recs, rpath, gm)
        tg = telegram_send.send(env, summary)
        log("Telegram: %s" % ("enviado %s parte(s)" % tg.get("parts_sent") if tg.get("ok")
                               else "FALHOU: %s" % tg.get("error")))
    else:
        log("Telegram: pulado (--no-telegram)")

    gm = g.metrics()
    state = {
        "finished_at": now_sp().isoformat(),
        "report_path": rpath,
        "agenda_status": agenda.get("status"),
        "telegram": tg,
        "recs_source": recs_source,
        "guardrails": gm,
    }
    with open(os.path.join(LOGS_DIR, "last_run.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    log("=== @daily-analyst END === %ss | %s/%s API | LLM R$%.2f | truncado=%s" % (
        gm["elapsed_seconds"], gm["api_calls"], gm["max_api_calls"], gm["llm_brl"], gm["truncated"]))

    # bloco final legível para a ETAPA 5
    print("\n----- RESUMO DA EXECUÇÃO -----")
    print(json.dumps({
        "chamadas_api": "%s/%s" % (gm["api_calls"], gm["max_api_calls"]),
        "tempo_s": gm["elapsed_seconds"],
        "custo_llm_brl": gm["llm_brl"],
        "telegram": ("OK (%s parte(s))" % tg.get("parts_sent")) if tg.get("ok") else (
            "pulado" if no_tg else "FALHOU: %s" % tg.get("error")),
        "relatorio": rpath,
        "agenda": agenda.get("status"),
        "truncado": gm["truncated"],
        "fonte_recomendacoes": recs_source,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        tb = traceback.format_exc()
        traceback.print_exc()
        # Grava crash no log para não perder o traceback quando stdout não está capturado
        try:
            crash_ts = now_sp().strftime("%Y-%m-%d %H:%M:%S")
            os.makedirs(LOGS_DIR, exist_ok=True)
            with open(os.path.join(LOGS_DIR, "run-%s.log" % now_sp().strftime("%Y-%m-%d")),
                      "a", encoding="utf-8") as _f:
                _f.write("[%s] CRASH FATAL:\n%s\n" % (crash_ts, tb))
        except Exception:
            pass
        sys.exit(1)
