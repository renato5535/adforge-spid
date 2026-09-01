"""
TikTok Content Posting API — Demo OAuth Flow
Sandbox: Teste Spis (App ID 7665870420104677384)

Como usar:
  1. Preencha CLIENT_SECRET abaixo (copiar da tela do Sandbox)
  2. pip install flask requests
  3. python demo_server.py
  4. Abrir http://localhost:8080 no navegador
  5. Clicar "Autorizar no TikTok" e completar o login com a Sandbox Test Account
  6. O callback vai chamar a Content Posting API e exibir a resposta
"""

import os
import json
import secrets
import hashlib
import base64
import requests
from urllib.parse import urlencode
from flask import Flask, redirect, request, render_template_string

# ─── Credenciais Sandbox ──────────────────────────────────────────────────────
CLIENT_KEY    = "sbawcvk2p9j02esyxo"
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "PREENCHER_AQUI")
REDIRECT_URI  = "https://spidcup.com.br/tiktok-callback/"
SCOPE         = "video.publish,user.info.basic"
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
SESSION = {}  # state, code_verifier


def _pkce_pair():
    """Gera (code_verifier, code_challenge) para PKCE S256."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge

# ── Templates inline ──────────────────────────────────────────────────────────
HOME_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>TikTok Content Posting API — Demo</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 800px; margin: 60px auto; padding: 0 20px; }
    h1 { color: #010101; }
    .badge { background: #fe2c55; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
    .btn { display: inline-block; background: #010101; color: white; padding: 14px 28px;
           border-radius: 8px; text-decoration: none; font-size: 16px; margin-top: 20px; }
    .info { background: #f5f5f5; padding: 16px; border-radius: 8px; margin-top: 20px; font-size: 14px; }
    code { background: #e8e8e8; padding: 2px 6px; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>TikTok <span class="badge">Sandbox</span> — Content Posting API</h1>
  <p>Esta demo mostra o fluxo OAuth 2.0 + chamada à Content Posting API.</p>
  <div class="info">
    <strong>App:</strong> SPID Cup Content (Sandbox: Teste Spis)<br>
    <strong>Client Key:</strong> <code>{{ client_key }}</code><br>
    <strong>Scope:</strong> <code>{{ scope }}</code><br>
    <strong>Redirect URI:</strong> <code>{{ redirect_uri }}</code>
  </div>
  <a class="btn" href="/authorize">▶ Autorizar no TikTok</a>
</body>
</html>
"""

RESULT_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Resultado — TikTok Demo</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; }
    h2 { color: {{ '#2e7d32' if success else '#c62828' }}; }
    pre { background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 8px; overflow-x: auto; font-size: 13px; }
    .step { margin: 10px 0; padding: 12px; border-left: 4px solid {{ '#4caf50' if success else '#f44336' }}; background: #f9f9f9; }
    .label { font-weight: bold; color: #555; font-size: 12px; text-transform: uppercase; }
    a { color: #010101; }
  </style>
</head>
<body>
  <h2>{{ '✅ Fluxo Concluído com Sucesso' if success else '⚠️ Erro no Fluxo' }}</h2>

  {% for step in steps %}
  <div class="step">
    <div class="label">{{ step.label }}</div>
    <pre>{{ step.data }}</pre>
  </div>
  {% endfor %}

  <p><a href="/">← Voltar ao início</a></p>
</body>
</html>
"""

ERROR_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Erro</title>
<style>body{font-family:Arial,sans-serif;max-width:700px;margin:60px auto;padding:0 20px;}
.err{background:#fce4e4;border-left:4px solid #f44336;padding:16px;border-radius:4px;}</style>
</head>
<body>
  <h2>Erro no fluxo OAuth</h2>
  <div class="err"><strong>{{ error }}</strong><br>{{ description }}</div>
  <p><a href="/">← Tentar novamente</a></p>
</body>
</html>
"""

# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template_string(HOME_HTML,
        client_key=CLIENT_KEY,
        scope=SCOPE,
        redirect_uri=REDIRECT_URI
    )

@app.route("/authorize")
def authorize():
    state = secrets.token_urlsafe(16)
    verifier, challenge = _pkce_pair()
    SESSION["state"] = state
    SESSION["code_verifier"] = verifier

    params = {
        "client_key": CLIENT_KEY,
        "scope": SCOPE,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}"
    return redirect(auth_url)

@app.route("/callback")
def callback():
    steps = []
    error = request.args.get("error")

    if error:
        return render_template_string(ERROR_HTML,
            error=error,
            description=request.args.get("error_description", "")
        )

    code = request.args.get("code")
    state = request.args.get("state")

    # Verificar state CSRF
    expected_state = SESSION.get("state")
    if state != expected_state:
        return render_template_string(ERROR_HTML,
            error="State mismatch",
            description=f"Esperado: {expected_state} | Recebido: {state}"
        )

    steps.append({"label": "1 · Código de autorização recebido", "data": f"code = {code[:12]}... (truncado)"})

    # ── Trocar code por access_token ──────────────────────────────────────────
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    token_payload = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": SESSION.get("code_verifier", ""),
    }
    token_resp = requests.post(token_url, data=token_payload,
                               headers={"Content-Type": "application/x-www-form-urlencoded"})
    token_data = token_resp.json()
    steps.append({
        "label": "2 · Token exchange (POST /v2/oauth/token/)",
        "data": json.dumps({k: (v[:12] + "..." if isinstance(v, str) and len(v) > 15 else v)
                            for k, v in token_data.items()}, indent=2)
    })

    access_token = token_data.get("access_token")
    if not access_token:
        return render_template_string(RESULT_HTML, success=False, steps=steps)

    # ── Buscar info do usuário ────────────────────────────────────────────────
    userinfo_resp = requests.get(
        "https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    userinfo = userinfo_resp.json()
    steps.append({
        "label": "3 · User info (GET /v2/user/info/)",
        "data": json.dumps(userinfo, indent=2, ensure_ascii=False)
    })

    # ── Iniciar upload via Content Posting API ────────────────────────────────
    post_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    post_payload = {
        "post_info": {
            "title": "Teste Content Posting API — SPID Cup",
            "privacy_level": "SELF_ONLY",
            "disable_duet": True,
            "disable_comment": True,
            "disable_stitch": True,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": 1024,          # placeholder
            "chunk_size": 1024,
            "total_chunk_count": 1,
        }
    }
    post_resp = requests.post(post_url,
        json=post_payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }
    )
    post_data = post_resp.json()
    steps.append({
        "label": "4 · Content Posting API — init upload (POST /v2/post/publish/video/init/)",
        "data": json.dumps(post_data, indent=2, ensure_ascii=False)
    })

    success = post_resp.status_code in (200, 201) or post_data.get("data") is not None
    return render_template_string(RESULT_HTML, success=success, steps=steps)


if __name__ == "__main__":
    if CLIENT_SECRET == "PREENCHER_AQUI":
        print("\n⚠️  ATENÇÃO: Preencha CLIENT_SECRET no início do arquivo ou defina a variável:")
        print("    $env:TIKTOK_CLIENT_SECRET = 'seu-client-secret-aqui'\n")
    print("🚀 Servidor rodando em http://localhost:8080")
    print("   Abra o browser nesse endereço para iniciar o demo\n")
    app.run(host="0.0.0.0", port=8080, debug=False)
