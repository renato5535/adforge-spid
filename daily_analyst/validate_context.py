"""Validacao do contexto carregado pelo daily-analyst.
Exercita: context loading, phase detection, ROAS minimo e prompt template.
Nao faz chamada de API de campanha nem envia Telegram.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import load_context_files, now_sp
from recommender import _phase_roas_min, _build_context_block

EVENT_DATE = date(2026, 8, 28)


def main():
    print("\n======================================================")
    print("  @daily-analyst - VALIDATE CONTEXT (dry-run)")
    print("  Rodado em:", now_sp().strftime("%Y-%m-%d %H:%M:%S BRT"))
    print("======================================================\n")

    # 1. Context files
    print("-- 1. CONTEXT FILES --")
    ctx = load_context_files()
    for fname, content in ctx.items():
        size = len(content.encode("utf-8"))
        status = "OK" if content.strip() else "VAZIO/AUSENTE"
        print("  %-35s %6d bytes  [%s]" % (fname, size, status))

    # 2. Phase detection
    print("\n-- 2. DETECAO DE FASE --")
    today = now_sp().date()
    dias = (EVENT_DATE - today).days
    print("  EVENT_DATE        : %s (3a Etapa SPID CUP 2026)" % EVENT_DATE)
    print("  Hoje              : %s" % today)
    print("  Dias ate o evento : %d" % dias)

    if dias > 14:
        fase = "AQUECIMENTO (> 14 dias)"
    elif dias > 7:
        fase = "ACELERACAO  (8-14 dias)"
    else:
        fase = "SPRINT FINAL (<= 7 dias)"
    print("  Fase detectada    : %s" % fase)

    # 3. ROAS minimo
    roas_min = _phase_roas_min(dias)
    print("\n-- 3. ROAS MINIMO --")
    print("  ROAS minimo para a fase atual : %.1fx" % roas_min)
    print("  (Aquecimento=10x | Aceleracao=8x | Sprint=5x)")

    # 4. Prompt template (instrucao + cabecalho de contexto, sem dados sensiveis)
    print("\n-- 4. PROMPT LLM - INSTRUCAO + CABECALHO --\n")
    ctx_block = _build_context_block(ctx)
    if len(ctx_block) > 400:
        ctx_display = ctx_block[:400] + "\n[... +%d chars restantes ...]" % (len(ctx_block) - 400)
    else:
        ctx_display = ctx_block if ctx_block else "(nenhum)"

    instr = (
        "Voce e analista de trafego pago do AdForge. Reescreva as recomendacoes para o gestor "
        "da 3a Etapa SPID CUP 2026 de forma direta e consultiva (linguagem de paddock, sem jargao "
        "corporativo). Use os benchmarks e a estrutura de campanha fornecidos como referencia para "
        "calibrar thresholds e prioridades. Maximo 5 recomendacoes. "
        'Responda APENAS JSON: {"recomendacoes":[{"prioridade":"alta|media|baixa","acao":"","porque":"","impacto":""}]}'
        "\n\n--- CONTEXTO DE CAMPANHA (use como referencia) ---\n"
        + ctx_display
        + "\n\n--- DADOS DO DIA ---\n{...payload JSON de campanha aqui...}"
    )
    print(instr)

    # 5. Metricas do prompt
    print("\n-- 5. METRICAS DO PROMPT --")
    base_instr_len = len(instr) - len(ctx_display) + len(ctx_block)
    total_chars = base_instr_len + 800  # +800 para payload JSON real
    total_tokens = total_chars // 4
    custo_brl = total_tokens / 1000.0 * 0.02
    print("  Chars instrucao base        : ~%d" % (base_instr_len - len(ctx_block)))
    print("  Chars bloco de contexto     : %d" % len(ctx_block))
    print("  Chars totais est. c/ payload: ~%d" % total_chars)
    print("  Tokens estimados (chars/4)  : ~%d" % total_tokens)
    print("  Custo estimado Anthropic    : ~R$ %.4f" % custo_brl)

    print("\n======================================================")
    print("  VALIDACAO CONCLUIDA - nenhuma API externa chamada")
    print("======================================================\n")


if __name__ == "__main__":
    main()