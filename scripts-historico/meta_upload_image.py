import os, sys, json, urllib.request, urllib.parse
from pathlib import Path

def load_env():
    env = Path.home() / ".adforge" / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

def upload_image(path: str, name: str) -> str:
    load_env()
    token = os.environ["META_ACCESS_TOKEN"]
    account = os.environ["META_AD_ACCOUNT_ID"]
    api = os.environ.get("META_API_VERSION", "v25.0")

    fpath = Path(path)
    data = fpath.read_bytes()
    boundary = "----AdForgeImgBoundary"
    parts = []
    for k, v in {"access_token": token, "name": name}.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}'.encode() + b"\r\n")
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="filename"; filename="{fpath.name}"\r\nContent-Type: image/png\r\n\r\n'.encode())
    parts.append(data)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)

    url = f"https://graph.facebook.com/{api}/{account}/adimages"
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        result = json.loads(r.read())
    images = result.get("images", {})
    for fname, info in images.items():
        print(f"OK {fname} -> hash: {info['hash']}")
        return info["hash"]
    print(f"ERR: {result}")
    return ""

if __name__ == "__main__":
    import sys
    hash_val = upload_image(sys.argv[1], sys.argv[2])
    print(f"IMAGE_HASH:{hash_val}")
