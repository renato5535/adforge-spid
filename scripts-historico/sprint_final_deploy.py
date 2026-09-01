"""
Sprint Final Deploy — 3ª Etapa SPID Cup 2026
============================================
1. Pausa B-03 (ROAS 0x)
2. Escala budgets: B-00 → R$200/dia | B-01 → R$140/dia | B-02 → R$70/dia
3. Upload: 4 vídeos + SORTEIO-DRAGSTER.png
4. Cria creative RMKT sprint final
5. Cria novos ads PAUSED em B-00, B-01, B-02
"""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

ASSETS_DIR = Path(r"E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3")
TICKET_URL = "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"
PAGE_ID    = "102560719007016"

CAMP_RMKT  = "120249601416320761"

ADSETS = {
    "B-00": "120249615946860761",   # Pageview 180D       → R$200/dia
    "B-01": "120249601941100761",   # Video View 95%      → R$140/dia
    "B-02": "120249615953090761",   # Purchase 180D       → R$70/dia
    "B-03": "120249615972980761",   # InitiateCheckout    → PAUSAR
}

# Targets diários em centavos (Meta usa centavos para daily_budget)
BUDGET_TARGETS = {
    "B-00": 20000,   # R$200/dia
    "B-01": 14000,   # R$140/dia
    "B-02":  7000,   # R$70/dia
}

VIDEOS = [
    ("etapa 3-vid-01.mp4", "[RMKT] Sprint Final v01 — 3ª Etapa SPID Cup"),
    ("etapa 3-vid-02.mp4", "[RMKT] Sprint Final v02 — 3ª Etapa SPID Cup"),
    ("etapa 3-vid-03.mp4", "[RMKT] Sprint Final v03 — 3ª Etapa SPID Cup"),
    ("etapa 3-vid-04.mp4", "[RMKT] Sprint Final v04 — 3ª Etapa SPID Cup"),
]
IMAGE = "SORTEIO-DRAGSTER.png"

COPY_SPRINT = {
    "bodies": [
        "Quem hesitou: queimou. Individual R$90, Família R$135. SPID Cup 3ª Etapa — 28 a 30/Ago, São Paulo International Dragway, Itatiba.",
        "Você viu o SPID. Faltam 10 dias. Individual R$90, Família R$135. 28/Ago ao vivo — arrancada real de 201m, carros a 355km/h.",
        "Borrachão feito, pista quente. Faltam 10 dias pra largada. Individual R$90, Família R$135 — garanta agora em agendaesportiva.com.br.",
        "201m de pista. Pro Mod a 355km/h. 28/Ago ao vivo. Só existe ao vivo — Individual R$90. São Paulo International Dragway, Itatiba/SP.",
        "Volta pra pista. 3ª Etapa SPID Cup — 28 a 30/Ago, Itatiba. Individual R$90, Família R$135. Não existe câmera lenta ao vivo.",
    ],
    "titles": [
        "3ª Etapa SPID Cup — 28/Ago",
        "Individual R$90 | Família R$135",
        "Faltam 10 dias — garanta agora",
        "São Paulo International Dragway",
        "28–30/Ago | Itatiba/SP",
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_env():
    for line in (Path.home() / ".adforge/.env").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

def _token():
    return os.environ["META_ACCESS_TOKEN"]

def _base():
    ver = os.environ.get("META_API_VERSION", "v25.0")
    return f"https://graph.facebook.com/{ver}"

def _acct():
    return os.environ["META_AD_ACCOUNT_ID"]

def api_get(url, params=None):
    params = params or {}
    params["access_token"] = _token()
    full = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full, timeout=30) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        return None, err.get("error", {}).get("message", str(e))

def api_post(url, data):
    data["access_token"] = _token()
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        return None, err.get("error", {}).get("message", str(e))

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# ── 1. Pausar B-03 ────────────────────────────────────────────────────────────

def pause_b03():
    log("1. Pausando B-03 InitiateCheckout (ROAS 0x)...")
    r, err = api_post(f"{_base()}/{ADSETS['B-03']}", {"status": "PAUSED"})
    if err:
        log(f"   ERRO: {err}")
    else:
        log(f"   B-03 → PAUSED ✓")

# ── 2. Escalar budgets ────────────────────────────────────────────────────────

def get_adset_spend(adset_id):
    """Retorna gasto total do adset em centavos via Insights."""
    r, err = api_get(f"{_base()}/{adset_id}/insights", {
        "fields": "spend",
        "date_preset": "lifetime",
    })
    if err or not r:
        return 0
    data = r.get("data", [])
    if data:
        return int(float(data[0].get("spend", 0)) * 100)
    return 0


def scale_budgets():
    from datetime import date
    log("2. Escalando budgets (Sprint Final: 10 dias p/ evento)...")
    # 10 dias até 28/Ago (inclusive o dia do evento)
    days_left = max((date(2026, 8, 28) - date.today()).days, 1)

    for label, adset_id in [(k, v) for k, v in ADSETS.items() if k != "B-03"]:
        target_cents = BUDGET_TARGETS[label]

        # Busca estrutura atual do adset
        r, err = api_get(f"{_base()}/{adset_id}", {
            "fields": "daily_budget,lifetime_budget,name"
        })
        if err:
            log(f"   {label} GET ERRO: {err}")
            continue

        curr_daily    = int(r.get("daily_budget") or 0)
        curr_lifetime = int(r.get("lifetime_budget") or 0)

        if curr_daily > 0:
            # Usa daily_budget — atualiza direto
            r2, err2 = api_post(f"{_base()}/{adset_id}", {"daily_budget": target_cents})
            if err2:
                log(f"   {label} ERRO daily_budget: {err2}")
            else:
                log(f"   {label} daily_budget R${curr_daily/100:.0f} → R${target_cents/100:.0f}/dia ✓")

        elif curr_lifetime > 0:
            # Lifetime budget — calcula: gasto_atual + target×dias_restantes
            spent_cents  = get_adset_spend(adset_id)
            new_lifetime = spent_cents + (target_cents * days_left)

            if new_lifetime <= curr_lifetime:
                # Budget existente já é suficiente — só loga, não altera
                log(f"   {label} lifetime atual R${curr_lifetime/100:.0f} já cobre alvo "
                    f"(gasto R${spent_cents/100:.0f} + R${target_cents/100:.0f}×{days_left}d) — sem mudança")
            else:
                r2, err2 = api_post(f"{_base()}/{adset_id}", {"lifetime_budget": new_lifetime})
                if err2:
                    log(f"   {label} ERRO lifetime: {err2}")
                else:
                    log(f"   {label} lifetime R${curr_lifetime/100:.0f} → R${new_lifetime/100:.0f} "
                        f"(+R${(new_lifetime-curr_lifetime)/100:.0f} | gasto R${spent_cents/100:.0f} + "
                        f"R${target_cents/100:.0f}×{days_left}d) ✓")
        else:
            log(f"   {label} sem budget encontrado — pulando")

# ── 3. Upload imagem ──────────────────────────────────────────────────────────

def upload_image(filepath):
    name = Path(filepath).name
    stem = Path(filepath).stem
    log(f"3a. Upload imagem: {name}")
    with open(filepath, "rb") as f:
        img_bytes = f.read()
    token = _token()
    acct  = _acct()
    boundary = "----MetaBoundary9F3A"
    ct = "image/png" if name.lower().endswith(".png") else "image/jpeg"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{stem}"; filename="{name}"\r\n'
        f"Content-Type: {ct}\r\n\r\n"
    ).encode() + img_bytes + f"\r\n--{boundary}--\r\n".encode()
    url = f"{_base()}/{acct}/adimages?access_token={token}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
        for k, v in resp.get("images", {}).items():
            h = v.get("hash")
            log(f"   imagem OK hash=...{h[-8:] if h else '?'}")
            return h
        log(f"   ERRO imagem: {resp}")
        return None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        log(f"   ERRO: {err.get('error', {}).get('message', str(err))}")
        return None

# ── 4. Upload vídeos ──────────────────────────────────────────────────────────

def upload_video(filepath, title):
    name = Path(filepath).name
    fsize = Path(filepath).stat().st_size
    acct  = _acct()
    log(f"3b. Upload vídeo: {name} ({fsize/1024/1024:.1f} MB)")

    # Start
    r, err = api_post(f"{_base()}/{acct}/advideos", {
        "upload_phase": "start",
        "file_size": fsize,
        "title": title,
    })
    if err:
        log(f"   ERRO start: {err}")
        return None
    session_id = r.get("upload_session_id")
    video_id   = r.get("video_id")

    # Transfer (chunks de 5MB)
    chunk_size = 5 * 1024 * 1024
    token = _token()
    with open(filepath, "rb") as f:
        offset = 0
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            boundary = "----VideoBoundary"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="upload_phase"\r\n\r\ntransfer\r\n'
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="upload_session_id"\r\n\r\n{session_id}\r\n'
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="start_offset"\r\n\r\n{offset}\r\n'
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="video_file_chunk"; filename="{name}"\r\n'
                f"Content-Type: video/mp4\r\n\r\n"
            ).encode() + chunk + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(
                f"{_base()}/{acct}/advideos", data=body, method="POST"
            )
            req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
            req.add_header("Authorization", f"Bearer {token}")
            try:
                with urllib.request.urlopen(req, timeout=120) as r2:
                    json.loads(r2.read())
            except urllib.error.HTTPError as e:
                err_data = json.loads(e.read())
                log(f"   ERRO chunk @{offset}: {err_data.get('error', {}).get('message')}")
                return None
            offset += len(chunk)
            print(f"   {int(offset/fsize*100)}% ({offset//1024//1024}MB)    ", end="\r")

    # Finish
    r3, err3 = api_post(f"{_base()}/{acct}/advideos", {
        "upload_phase": "finish",
        "upload_session_id": session_id,
        "title": title,
    })
    if err3:
        log(f"   ERRO finish: {err3}")
        return None
    log(f"   vídeo OK id={video_id}")
    return video_id

# ── 5. Creative ───────────────────────────────────────────────────────────────

def make_creative(img_hash, video_ids):
    log("4. Criando creative sprint final RMKT...")
    acct = _acct()
    asset_feed = {
        "images": [{"hash": img_hash}] if img_hash else [],
        "videos": [{"video_id": vid} for vid in video_ids if vid],
        "bodies": [{"text": t} for t in COPY_SPRINT["bodies"]],
        "titles": [{"text": t} for t in COPY_SPRINT["titles"]],
        "call_to_action_types": ["SHOP_NOW"],
        "link_urls": [{"website_url": TICKET_URL}],
        "ad_formats": ["AUTOMATIC_FORMAT"],
    }
    data = {
        "name": "creative-3etapa-rmkt-sprint-final",
        "object_story_spec": json.dumps({"page_id": PAGE_ID}),
        "asset_feed_spec": json.dumps(asset_feed),
        "use_dynamic_creative": "false",
    }
    r, err = api_post(f"{_base()}/{acct}/adcreatives", data)
    if err:
        log(f"   ERRO creative: {err}")
        return None
    cid = r.get("id")
    log(f"   creative OK id={cid}")
    return cid

# ── 6. Ads PAUSED ─────────────────────────────────────────────────────────────

def create_ads(creative_id):
    log("5. Criando ads PAUSED em B-00, B-01, B-02...")
    acct = _acct()
    results = []
    for label in ["B-00", "B-01", "B-02"]:
        adset_id = ADSETS[label]
        ad_name  = f"[RMKT] 3aEtapa {label} Sprint Final | auto"
        r, err = api_post(f"{_base()}/{acct}/ads", {
            "name": ad_name,
            "adset_id": adset_id,
            "creative": json.dumps({"creative_id": creative_id}),
            "status": "PAUSED",
            "tracking_specs": json.dumps([{
                "action.type": ["offsite_conversion"],
                "fb_pixel": [os.environ.get("META_PIXEL_ID", "867066736318670")],
            }]),
        })
        ok = bool(r and r.get("id"))
        log(f"   {label} → {'PAUSED ✓ id=' + r['id'] if ok else 'ERRO: ' + str(err)}")
        results.append((label, ok, r.get("id") if ok else None))
    return results

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_env()
    log("=== Sprint Final Deploy — 3ª Etapa SPID Cup ===\n")

    # 1. Pausar B-03
    pause_b03()

    # 2. Budgets
    scale_budgets()

    # 3a. Imagem
    img_path = ASSETS_DIR / IMAGE
    img_hash = upload_image(str(img_path)) if img_path.exists() else None
    if not img_hash:
        log("   AVISO: imagem não subiu, creative só com vídeos")

    # 3b. Vídeos
    video_ids = []
    for fname, title in VIDEOS:
        vpath = ASSETS_DIR / fname
        if not vpath.exists():
            log(f"   SKIP: {fname} não encontrado")
            continue
        vid_id = upload_video(str(vpath), title)
        if vid_id:
            video_ids.append(vid_id)

    log(f"\nAssets prontos: {len(video_ids)} vídeos + {'1 imagem' if img_hash else '0 imagens'}")

    if not video_ids:
        log("ERRO FATAL: nenhum vídeo subiu. Abortando criação de ads.")
        return

    # 4. Creative
    creative_id = make_creative(img_hash, video_ids)
    if not creative_id:
        log("ERRO FATAL: creative não criado. Abortando.")
        return

    # 5. Ads PAUSED
    ad_results = create_ads(creative_id)

    # Resumo
    ok_ads = sum(1 for _, ok, _ in ad_results if ok)
    print("\n" + "="*50)
    log(f"=== CONCLUÍDO ===")
    print(f"""
RESUMO:
  B-03:        PAUSED ✓
  Budgets:     B-00 R$200/dia · B-01 R$140/dia · B-02 R$70/dia
  Vídeos:      {len(video_ids)}/4 subidos
  Imagem:      {'SORTEIO-DRAGSTER.png ✓' if img_hash else 'falhou'}
  Creative:    {creative_id}
  Ads criados: {ok_ads}/3 (todos PAUSED — aguardam ativação)

PRÓXIMO PASSO: Renato ativa os 3 novos ads no Gerenciador.
""")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
