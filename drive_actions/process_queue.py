"""
Processador de fila Drive → Meta.

EXECUTA DENTRO DE SESSÃO CLAUDE (requer Drive MCP e meta_actions).

Uso típico (início de sessão):
    from drive_actions.process_queue import check_and_report_queue
    check_and_report_queue()

Uso completo (com adset_id definido):
    from drive_actions.process_queue import process_pending
    process_pending()

Este módulo NÃO é executado pelo bot — é chamado por Claude
quando Renato abre uma sessão e há pastas na fila.
"""
import json
import sys
import os
from pathlib import Path

# Adiciona raiz do .adforge ao path
_root = str(Path.home() / ".adforge")
if _root not in sys.path:
    sys.path.insert(0, _root)

from drive_actions.drive_queue import (
    list_pending, mark_done, mark_error, has_pending
)

# Extensões de imagem aceitas para upload no Meta
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}

# Pasta temporária para downloads
_TEMP_DIR = Path.home() / ".adforge" / "temp" / "drive_assets"


def check_and_report_queue() -> str:
    """
    Chamado no início de cada sessão Claude para verificar se há
    pastas aguardando processamento.

    Retorna string de status para exibição.
    """
    pending = list_pending()
    if not pending:
        return ""

    lines = ["⚠️ DRIVE QUEUE — %d pasta(s) aguardando processamento:" % len(pending)]
    for item in pending:
        lines.append(
            "  #%d | %s | adset: %s | adicionado: %s"
            % (item["id"], item["label"], item.get("adset_id") or "NÃO DEFINIDO",
               item["added_at"][:16])
        )
    lines.append("")
    lines.append("Para processar: chame process_pending() deste módulo")
    lines.append("ou use o fluxo manual no Drive MCP + meta_actions.py")
    return "\n".join(lines)


def get_image_files_from_folder(folder_id: str, drive_files: list) -> list:
    """
    Filtra arquivos de imagem de uma lista retornada pelo Drive MCP.

    drive_files: lista de dicts com campos 'id', 'title', 'mimeType', etc.
    Retorna lista de arquivos de imagem/vídeo.
    """
    result = []
    for f in drive_files:
        name = f.get("title", "")
        mime = f.get("mimeType", "")
        ext  = Path(name).suffix.lower()
        if ext in _IMAGE_EXTS or mime.startswith("image/"):
            result.append({
                "drive_id":  f["id"],
                "name":      name,
                "type":      "image",
                "mime":      mime,
                "view_url":  f.get("viewUrl", ""),
            })
        elif ext in _VIDEO_EXTS or mime.startswith("video/"):
            result.append({
                "drive_id":  f["id"],
                "name":      name,
                "type":      "video",
                "mime":      mime,
                "view_url":  f.get("viewUrl", ""),
            })
    return result


def save_download(file_id: str, filename: str, content_bytes: bytes) -> Path:
    """Salva conteúdo baixado do Drive em pasta temp."""
    _TEMP_DIR.mkdir(parents=True, exist_ok=True)
    dest = _TEMP_DIR / filename
    dest.write_bytes(content_bytes)
    return dest


def build_campaign_name(folder_label: str, file_name: str) -> str:
    """Gera nome do ad a partir do contexto da pasta e arquivo."""
    base = Path(file_name).stem
    return "[AdForge] %s — %s" % (folder_label[:30], base[:30])


def default_link() -> str:
    """URL de destino padrão para ads SPID."""
    env_path = Path.home() / ".adforge" / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("SPID_INGRESSO_URL"):
            return line.split("=", 1)[1].strip("'\" ")
    return "https://www.spidcup.com.br/spidcup-ingressos/"


def format_summary_for_telegram(folder_label: str, ads: list) -> str:
    """Formata mensagem de resumo para enviar via Telegram."""
    if not ads:
        return "⚠️ Nenhum criativo criado para %s" % folder_label

    lines = [
        "✅ <b>Drive → Meta concluído</b>",
        "",
        "Pasta: <b>%s</b>" % folder_label,
        "Criativos criados: <b>%d</b>" % len(ads),
        "Status: <b>PAUSADOS</b> (aguardando sua aprovação)",
        "",
    ]
    for ad in ads:
        lines.append(
            "• <code>%s</code> — ad_id: <code>%s</code>"
            % (ad.get("name", "?")[:40], ad.get("ad_id", "?"))
        )
    lines += [
        "",
        "Para ativar: acesse o Gerenciador Meta ou use /ativar_ad AD_ID",
    ]
    return "\n".join(lines)
