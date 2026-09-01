"""
Verificação de início de sessão — executado pelo Claude ao abrir nova conversa.

Uso (em qualquer sessão Claude):
    from drive_actions.session_start import check_drive_queue
    check_drive_queue()

Se houver itens na fila, imprime um aviso com instruções de processamento.
O próprio Claude então decide se processa (usando Drive MCP + meta_actions).
"""
import sys
from pathlib import Path

_root = str(Path.home() / ".adforge")
if _root not in sys.path:
    sys.path.insert(0, _root)

from drive_actions.drive_queue import list_pending, has_pending


def check_drive_queue(auto_print: bool = True) -> list:
    """
    Retorna lista de pastas pendentes.
    Se auto_print=True, imprime aviso no terminal.
    """
    pending = list_pending()
    if not pending and auto_print:
        return []

    if auto_print and pending:
        print("\n" + "="*60)
        print("⚠️  DRIVE QUEUE — %d pasta(s) aguardando" % len(pending))
        print("="*60)
        for item in pending:
            print("  #%d | %s" % (item["id"], item["label"]))
            print("     folder_id : %s" % item["folder_id"])
            print("     adset_id  : %s" % (item.get("adset_id") or "NÃO DEFINIDO ← precisa informar"))
            print("     adicionado: %s" % item["added_at"][:16])
        print()
        print("Para processar:")
        print("  1. Use o Drive MCP para listar arquivos da pasta")
        print("  2. Baixe as imagens com download_file_content")
        print("  3. Chame meta_actions.create_ad_from_image() para cada uma")
        print("  4. Chame mark_done(folder_id, ads_created=[...])")
        print("="*60 + "\n")

    return pending


if __name__ == "__main__":
    check_drive_queue()
