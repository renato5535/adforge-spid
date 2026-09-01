"""
Faz upload de um video local para a biblioteca de ad videos do Meta.
Uso: python meta_upload_video.py <caminho_do_video> "<titulo>"
Retorna: video ID pronto para usar no meta_create_ads.py
"""
import os, sys, json, urllib.request, urllib.parse, mimetypes
from pathlib import Path

def load_env():
    env = Path.home() / ".adforge" / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

def upload_video(video_path: str, title: str) -> str:
    load_env()
    TOKEN   = os.environ["META_ACCESS_TOKEN"]
    ACCOUNT = os.environ["META_AD_ACCOUNT_ID"]
    API_VER = os.environ.get("META_API_VERSION", "v25.0")
    BASE    = f"https://graph.facebook.com/{API_VER}"

    vpath = Path(video_path)
    if not vpath.exists():
        print(f"ERRO: Arquivo nao encontrado: {vpath}", file=sys.stderr)
        sys.exit(1)

    file_size = vpath.stat().st_size
    mime = mimetypes.guess_type(str(vpath))[0] or "video/mp4"

    print(f"Iniciando upload: {vpath.name} ({file_size / 1024 / 1024:.1f} MB)")

    # Fase 1: iniciar upload resumavel
    init_url = f"https://graph.facebook.com/{API_VER}/{ACCOUNT}/advideos"
    boundary = "----AdForgeUploadBoundary"

    # Primeiro registrar o video (sem conteudo) para obter upload_url
    metadata = {
        "file_size": str(file_size),
        "file_name": vpath.name,
        "title": title,
        "access_token": TOKEN,
    }
    params = urllib.parse.urlencode(metadata)
    req = urllib.request.Request(
        f"{init_url}?{params}",
        method="POST",
        data=b"",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        init_data = json.loads(r.read())

    video_id    = init_data.get("id")
    upload_url  = init_data.get("upload_url")

    if not upload_url:
        # Fallback: multipart upload direto
        print("Usando upload multipart direto...")
        import http.client, io
        boundary_b = b"--" + boundary.encode()
        body_parts = []
        for key, val in {"access_token": TOKEN, "title": title}.items():
            body_parts.append(boundary_b + f'\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{val}'.encode() + b"\r\n")
        body_parts.append(
            boundary_b +
            f'\r\nContent-Disposition: form-data; name="source"; filename="{vpath.name}"\r\nContent-Type: {mime}\r\n\r\n'.encode()
        )
        body_parts.append(vpath.read_bytes())
        body_parts.append(b"\r\n" + boundary_b + b"--\r\n")
        body = b"".join(body_parts)

        req2 = urllib.request.Request(
            init_url,
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req2, timeout=300) as r2:
            result = json.loads(r2.read())
            video_id = result.get("id")
    else:
        # Upload resumavel por chunks
        chunk_size = 5 * 1024 * 1024  # 5MB
        uploaded = 0
        with open(vpath, "rb") as f:
            while uploaded < file_size:
                chunk = f.read(chunk_size)
                end_byte = uploaded + len(chunk) - 1
                headers = {
                    "Authorization": f"OAuth {TOKEN}",
                    "Content-Type": mime,
                    "Content-Range": f"bytes {uploaded}-{end_byte}/{file_size}",
                    "offset": str(uploaded),
                    "file_size": str(file_size),
                }
                req = urllib.request.Request(upload_url, data=chunk, method="POST", headers=headers)
                with urllib.request.urlopen(req, timeout=120) as r:
                    resp = json.loads(r.read())
                uploaded += len(chunk)
                pct = int(uploaded / file_size * 100)
                print(f"  {pct}% ({uploaded // 1024 // 1024} MB)", end="\r")

    print(f"\nUpload concluido! Video ID: {video_id}")
    print(f"Use: python meta_create_ads.py --video-id {video_id}")
    return video_id

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python meta_upload_video.py <video.mp4> \"<titulo>\"")
        sys.exit(1)
    upload_video(sys.argv[1], sys.argv[2])
