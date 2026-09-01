"""
AdForge Verify Loop — integração @verifier no pipeline do daily-analyst.

Fluxo:
  daily-analyst gera relatório
       ↓
  verify_loop carrega o relatório mais recente
       ↓
  @verifier puxa dados frescos da Meta API
       ↓
  veredicto OK  → relatório segue para o bot Telegram normalmente
  veredicto WARN → relatório vai com flag de aviso
  veredicto ALERT → bloqueia envio, notifica Renato direto

Uso:
  python verify_loop.py                    # roda uma vez
  python verify_loop.py --watch 300        # loop contínuo a cada 5min

Integração com daily-analyst:
  Em run.py, adicionar após gerar o relatório:
      from verifier.verify_loop import run_verification
      ok = run_verification(reported_data)
      if not ok: sys.exit(2)  # sinaliza falha para o scheduler
"""
import sys
import json
import time
import argparse
from pathlib import Path

# Adiciona ~/.adforge ao path
sys.path.insert(0, str(Path.home() / ".adforge"))
from verifier.verifier import verify


def load_latest_report() -> dict | None:
    """Carrega o relatório mais recente gerado pelo daily-analyst."""
    report_dir = Path.home() / ".adforge" / "daily_analyst" / "reports"
    if not report_dir.exists():
        return None
    reports = sorted(report_dir.glob("*.json"), reverse=True)
    if not reports:
        return None
    try:
        return json.loads(reports[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def run_verification(reported_data: dict | None = None) -> bool:
    """
    Executa verificação. Retorna True se OK ou WARN, False se ALERT.
    Chamável diretamente pelo daily-analyst.
    """
    if reported_data is None:
        reported_data = load_latest_report()

    result = verify(reported=reported_data)

    verdict = result["verdict"]
    real    = result["real_data"]

    print(f"\n{'='*50}")
    print(f"@verifier — {verdict}")
    print(f"Spend real hoje: R${real['spend_today']:.2f}")
    print(f"ROAS real: {real['roas_today']:.1f}x")
    print(f"Compras reais: {real['purchases_today']}")
    print(f"Adsets ativos: {real['active_adsets']} ({real['zero_delivery_count']} sem entrega)")

    if result["issues"]:
        print("\nIssues encontrados:")
        for issue in result["issues"]:
            print(f"  [{issue['severity']}] {issue['msg']}")
    print(f"{'='*50}\n")

    return verdict != "ALERT"


def watch_loop(interval_seconds: int):
    """Roda o verificador em loop contínuo (uso em campanhas críticas)."""
    print(f"[verify_loop] modo watch — verificando a cada {interval_seconds}s")
    while True:
        try:
            run_verification()
        except Exception as e:
            print(f"[verify_loop] erro: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AdForge @verifier loop")
    parser.add_argument("--watch", type=int, metavar="SECONDS",
                        help="Modo contínuo: intervalo em segundos entre verificações")
    args = parser.parse_args()

    if args.watch:
        watch_loop(args.watch)
    else:
        ok = run_verification()
        sys.exit(0 if ok else 1)
