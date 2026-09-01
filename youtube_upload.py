"""
AdForge - YouTube Data API v3 upload + schedule para Shorts.
Upload via requests (sem httplib2) para compatibilidade com Windows.

Uso:
  python youtube_upload.py <video.mp4> "<titulo>" "<descricao>" <YYYY-MM-DDTHH:MM:SS>
"""

import os, sys, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

CREDENTIALS_FILE = Path.home() / ".adforge" / "youtube_credentials.json"
TOKEN_FILE       = Path.home() / ".adforge" / "youtube_token.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CATEGORY_ID = "2"   # Autos & Vehicles
UPLOAD_URL  = "https://www.googleapis.com/upload/youtube/v3/videos"
API_URL     = "https://www.googleapis.com/youtube/v3/videos"


def get_credentials():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"Arquivo de credenciais nao encontrado: {CREDENTIALS_FILE}")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"  Token salvo em: {TOKEN_FILE}")

    return creds


def upload_video(video_path: str, title: str, description: str, scheduled_at: str = None,
                 tags: list = None, privacy: str = "public"):
    import requests

    video_path = Path(video_path)
    if not video_path.exists():
        print(f"Arquivo nao encontrado: {video_path}")
        sys.exit(1)

    creds = get_credentials()

    # -- Montar metadados -------------------------------------------------------
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags or ["SPIDCup", "DragRacing", "Itatiba", "ArrancadaBrasil", "spidcup2026"],
            "categoryId": CATEGORY_ID,
            "defaultLanguage": "pt-BR",
        },
        "status": {"selfDeclaredMadeForKids": False},
    }

    if scheduled_at:
        dt_local = datetime.fromisoformat(scheduled_at)
        if dt_local.tzinfo is None:
            dt_local = dt_local.replace(tzinfo=timezone(timedelta(hours=-3)))
        dt_utc = dt_local.astimezone(timezone.utc)
        publish_at = dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        body["status"]["publishAt"]      = publish_at
        body["status"]["privacyStatus"]  = "private"
        print(f"  Agendado: {scheduled_at} BRT -> {publish_at} UTC")
    else:
        body["status"]["privacyStatus"] = privacy

    file_size = video_path.stat().st_size
    print(f"\n[UPLOAD] {video_path.name} ({file_size / 1_048_576:.1f} MB)")
    print(f"  Titulo: {title}")

    # -- Step 1: iniciar upload resumable ----------------------------------------
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {creds.token}"})

    parts = ",".join(body.keys())
    init_resp = session.post(
        UPLOAD_URL,
        params={"uploadType": "resumable", "part": parts},
        headers={
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(file_size),
        },
        json=body,
        timeout=30,
    )
    init_resp.raise_for_status()
    upload_uri = init_resp.headers["Location"]

    # -- Step 2: upload em chunks ------------------------------------------------
    chunk_size = 5 * 1024 * 1024   # 5 MB
    uploaded   = 0

    with open(video_path, "rb") as f:
        while uploaded < file_size:
            chunk = f.read(chunk_size)
            chunk_len  = len(chunk)
            end_byte   = uploaded + chunk_len - 1

            chunk_resp = session.put(
                upload_uri,
                headers={
                    "Authorization": f"Bearer {creds.token}",
                    "Content-Length": str(chunk_len),
                    "Content-Range": f"bytes {uploaded}-{end_byte}/{file_size}",
                    "Content-Type": "video/mp4",
                },
                data=chunk,
                timeout=120,
            )

            uploaded += chunk_len
            pct = int(uploaded / file_size * 100)
            print(f"  Upload: {pct}%", end="\r")

            if chunk_resp.status_code in (200, 201):
                data = chunk_resp.json()
                video_id = data["id"]
                url = f"https://youtube.com/shorts/{video_id}?feature=share"
                print(f"\n  Upload concluido!")
                print(f"  ID: {video_id}")
                print(f"  URL: {url}")
                return video_id, url

            if chunk_resp.status_code not in (308,):
                print(f"\n  Erro no chunk: {chunk_resp.status_code} {chunk_resp.text[:200]}")
                sys.exit(1)

    print("\n  Upload completo sem resposta final — verifique o YouTube Studio")
    return None, None


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    video_path  = sys.argv[1]
    title       = sys.argv[2]
    description = sys.argv[3]
    scheduled   = sys.argv[4] if len(sys.argv) > 4 else None

    upload_video(video_path, title, description, scheduled_at=scheduled)


if __name__ == "__main__":
    main()
