"""
Gerencia a fila de pastas do Google Drive aguardando processamento.

O bot (Python) escreve na fila.
Claude (sessão interativa) lê e processa via Drive MCP.
"""
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

_QUEUE_FILE = Path.home() / ".adforge" / "drive_queue.json"
SP_TZ = timezone(timedelta(hours=-3))


def _load():
    if not _QUEUE_FILE.exists():
        return {"items": []}
    try:
        return json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"items": []}


def _save(data):
    _QUEUE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_folder(folder_id: str, label: str = "", adset_id: str = "") -> dict:
    """
    Adiciona uma pasta à fila de processamento.

    folder_id: ID do Google Drive (extraído do URL ou informado manualmente)
    label:     Nome descritivo (ex: '3ª Etapa SPID CUP 2026')
    adset_id:  Adset onde os ads serão criados (pode ser preenchido depois)
    """
    data = _load()
    item = {
        "id":        len(data["items"]) + 1,
        "folder_id": folder_id,
        "label":     label or folder_id,
        "adset_id":  adset_id,
        "status":    "pending",
        "added_at":  datetime.now(SP_TZ).isoformat(),
        "ads_created": [],
    }
    data["items"].append(item)
    _save(data)
    return item


def list_pending() -> list:
    return [i for i in _load()["items"] if i["status"] == "pending"]


def list_all() -> list:
    return _load()["items"]


def mark_done(folder_id: str, ads_created: list):
    data = _load()
    for item in data["items"]:
        if item["folder_id"] == folder_id and item["status"] == "pending":
            item["status"]      = "done"
            item["done_at"]     = datetime.now(SP_TZ).isoformat()
            item["ads_created"] = ads_created
            break
    _save(data)


def mark_error(folder_id: str, error: str):
    data = _load()
    for item in data["items"]:
        if item["folder_id"] == folder_id and item["status"] == "pending":
            item["status"] = "error"
            item["error"]  = error
            break
    _save(data)


def has_pending() -> bool:
    return bool(list_pending())


def extract_folder_id(url_or_id: str) -> str:
    """
    Extrai o folder_id de um URL do Drive ou retorna o ID diretamente.

    Formatos aceitos:
    - https://drive.google.com/drive/folders/FOLDER_ID
    - https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing
    - FOLDER_ID (direto)
    """
    url_or_id = url_or_id.strip()
    if "drive.google.com" in url_or_id:
        parts = url_or_id.split("/folders/")
        if len(parts) > 1:
            return parts[1].split("?")[0].split("/")[0]
    return url_or_id
