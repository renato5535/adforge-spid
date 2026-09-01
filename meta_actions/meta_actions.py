"""
AdForge Meta Actions — criação autônoma de criativos e ads via API.

Fluxo principal:
  1. upload_image(path_ou_url)  → image_hash
  2. create_creative(...)       → creative_id
  3. create_ad(...)             → ad_id

Integração com bot Telegram (Fase 2):
  O bot chama action_from_recommendation(rec) com o dict de recomendação
  gerado pelo daily-analyst + verificado pelo @verifier.
  Retorna um resultado que o bot envia ao Renato para aprovação.
"""
import os
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# ── Carrega .env ──────────────────────────────────────────────────────────────
_env = Path.home() / ".adforge" / ".env"
for _line in _env.read_text(encoding="utf-8").splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        k, _, v = _line.partition("=")
        os.environ.setdefault(k.strip(), v.strip("'\""))

TOKEN      = os.environ["META_ACCESS_TOKEN"]
ACCOUNT    = os.environ["META_AD_ACCOUNT_ID"]
PAGE_ID    = os.environ["META_PAGE_ID"]
API_VER    = os.environ.get("META_API_VERSION", "v25.0")
BASE_URL   = f"https://graph.facebook.com/{API_VER}"


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get(path, params=None):
    p = dict(params or {})
    p["access_token"] = TOKEN
    qs = urllib.parse.urlencode(p)
    with urllib.request.urlopen(f"{BASE_URL}/{path}?{qs}", timeout=20) as r:
        return json.loads(r.read())

def _post(path, data):
    data["access_token"] = TOKEN
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f"{BASE_URL}/{path}", data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        err  = body.get("error", {})
        raise MetaAPIError(e.code, err.get("message", ""), err.get("code"), err.get("error_subcode")) from None

def _delete(path):
    qs = urllib.parse.urlencode({"access_token": TOKEN})
    req = urllib.request.Request(f"{BASE_URL}/{path}?{qs}", method="DELETE")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


class MetaAPIError(Exception):
    def __init__(self, http_status, message, code=None, subcode=None):
        self.http_status = http_status
        self.code        = code
        self.subcode     = subcode
        super().__init__(f"[{http_status}] {message} (code={code}, sub={subcode})")


# ── 1. Upload de imagem ───────────────────────────────────────────────────────

def upload_image(source: str) -> dict:
    """
    Faz upload de uma imagem para a biblioteca de imagens do Ad Account.

    source: caminho local (str/Path) ou URL pública de imagem.
    Retorna: {"hash": "...", "url": "...", "name": "..."}
    """
    source = str(source)

    if source.startswith("http://") or source.startswith("https://"):
        # Download temporário
        with urllib.request.urlopen(source, timeout=30) as r:
            image_bytes = r.read()
        filename = source.split("/")[-1].split("?")[0] or "image.jpg"
    else:
        image_bytes = Path(source).read_bytes()
        filename    = Path(source).name

    # Multipart form-data manual
    boundary = "----AdForgeBoundary7MA4YWxkTrZu0gW"
    body  = f"--{boundary}\r\n"
    body += f'Content-Disposition: form-data; name="access_token"\r\n\r\n{TOKEN}\r\n'
    body += f"--{boundary}\r\n"
    body += f'Content-Disposition: form-data; name="filename"; filename="{filename}"\r\n'
    body += "Content-Type: image/jpeg\r\n\r\n"
    body_bytes = body.encode() + image_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{BASE_URL}/{ACCOUNT}/adimages",
        data=body_bytes,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp  = json.loads(r.read())
            images = resp.get("images", {})
            first  = next(iter(images.values()))
            return {"hash": first["hash"], "url": first.get("url", ""), "name": filename}
    except urllib.error.HTTPError as e:
        body_err = json.loads(e.read())
        err = body_err.get("error", {})
        raise MetaAPIError(e.code, err.get("message", ""), err.get("code"), err.get("error_subcode")) from None


# ── 2. Criar criativo ─────────────────────────────────────────────────────────

def create_creative(
    image_hash: str,
    headline: str,
    body_text: str,
    link: str,
    name: str = None,
    call_to_action: str = "BUY_TICKETS",
    page_id: str = None,
) -> str:
    """
    Cria um ad creative com imagem já uploadada.
    Retorna creative_id (str).
    """
    page_id = page_id or PAGE_ID
    cta_map = {
        "BUY_TICKETS": "BUY_TICKETS",
        "LEARN_MORE":  "LEARN_MORE",
        "SIGN_UP":     "SIGN_UP",
        "GET_OFFER":   "GET_OFFER",
    }
    resp = _post(f"{ACCOUNT}/adcreatives", {
        "name": name or f"AdForge — {headline[:40]}",
        "object_story_spec": json.dumps({
            "page_id": page_id,
            "link_data": {
                "image_hash": image_hash,
                "link": link,
                "message": body_text,
                "name": headline,
                "call_to_action": {"type": cta_map.get(call_to_action, "BUY_TICKETS")},
            }
        })
    })
    return resp["id"]


# ── 3. Criar ad ───────────────────────────────────────────────────────────────

def create_ad(
    adset_id: str,
    creative_id: str,
    name: str,
    status: str = "PAUSED",
) -> str:
    """
    Cria um ad vinculado a um adset e creative.
    status='PAUSED' por segurança — Renato ativa manualmente ou via bot.
    Retorna ad_id (str).
    """
    resp = _post(f"{ACCOUNT}/ads", {
        "name": name,
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": status,
    })
    return resp["id"]


# ── 4. Pausar / ativar ad ────────────────────────────────────────────────────

def set_ad_status(ad_id: str, status: str) -> bool:
    """status: 'ACTIVE' | 'PAUSED'"""
    resp = _post(f"{ad_id}", {"status": status})
    return resp.get("success", False)

def pause_ad(ad_id: str) -> bool:
    return set_ad_status(ad_id, "PAUSED")

def activate_ad(ad_id: str) -> bool:
    return set_ad_status(ad_id, "ACTIVE")


# ── 5. Escalar budget de adset ───────────────────────────────────────────────

def scale_adset_budget(adset_id: str, daily_budget_brl: float) -> bool:
    """daily_budget_brl em reais (ex: 300.00 → R$300/dia)"""
    budget_cents = int(daily_budget_brl * 100)
    resp = _post(f"{adset_id}", {"daily_budget": budget_cents})
    return resp.get("success", False)


# ── 6. Pipeline completo: imagem → criativo → ad ────────────────────────────

def create_ad_from_image(
    image_source: str,
    headline: str,
    body_text: str,
    link: str,
    adset_id: str,
    ad_name: str,
    call_to_action: str = "BUY_TICKETS",
    auto_activate: bool = False,
) -> dict:
    """
    Pipeline completo: faz upload da imagem, cria criativo, cria ad (pausado).

    auto_activate=False: ad fica pausado até Renato aprovar via bot.
    auto_activate=True:  ad entra ativo imediatamente (usar só em campanhas activas).

    Retorna dict com image_hash, creative_id, ad_id, status.
    """
    print(f"[meta_actions] upload: {image_source}")
    img = upload_image(image_source)
    print(f"[meta_actions] imagem ok — hash {img['hash'][:8]}...")

    print(f"[meta_actions] criando criativo: {headline[:40]}")
    creative_id = create_creative(
        image_hash=img["hash"],
        headline=headline,
        body_text=body_text,
        link=link,
        call_to_action=call_to_action,
    )
    print(f"[meta_actions] creative_id: {creative_id}")

    status = "ACTIVE" if auto_activate else "PAUSED"
    print(f"[meta_actions] criando ad ({status}): {ad_name}")
    ad_id = create_ad(adset_id, creative_id, ad_name, status=status)
    print(f"[meta_actions] ad_id: {ad_id} — {status}")

    return {
        "image_hash":  img["hash"],
        "image_url":   img["url"],
        "creative_id": creative_id,
        "ad_id":       ad_id,
        "status":      status,
    }


# ── 7. Listar adsets ativos (helper para o bot) ──────────────────────────────

def list_active_adsets() -> list:
    """Retorna adsets com status ACTIVE ou seus dados básicos."""
    data = _get(f"{ACCOUNT}/adsets", {
        "effective_status": json.dumps(["ACTIVE"]),
        "fields": "id,name,daily_budget,status,effective_status",
        "limit": 50,
    })
    return data.get("data", [])


# ── CLI rápido para testes ────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

    if cmd == "list":
        adsets = list_active_adsets()
        print(f"{len(adsets)} adsets ativos:")
        for a in adsets:
            budget = int(a.get("daily_budget", 0)) / 100
            print(f"  {a['id']} | {a['name']} | R${budget:.0f}/dia")

    elif cmd == "test-upload":
        # python meta_actions.py test-upload /path/to/image.jpg
        path = sys.argv[2]
        result = upload_image(path)
        print(f"Upload OK: {result}")

    elif cmd == "test-pipeline":
        # python meta_actions.py test-pipeline <adset_id> <image_path>
        adset_id = sys.argv[2]
        image    = sys.argv[3]
        result   = create_ad_from_image(
            image_source=image,
            headline="3ª Etapa SPID CUP 2026",
            body_text="Garanta seu ingresso! Aceleração, adrenalina e família na pista.",
            link="https://www.spidcup.com.br/spidcup-ingressos/",
            adset_id=adset_id,
            ad_name="[AdForge] Teste Pipeline",
            auto_activate=False,
        )
        print(f"Pipeline OK: {json.dumps(result, indent=2)}")
