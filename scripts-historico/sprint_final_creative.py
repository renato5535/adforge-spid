"""
Sprint Final — Parte 2: Creative + Ads PAUSED
(Vídeos já subidos na Parte 1)
"""
import os, sys, json, time, urllib.request, urllib.parse
from pathlib import Path

TICKET_URL = "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"
PAGE_ID    = "102560719007016"

ADSETS = {
    "B-00": "120249615946860761",
    "B-01": "120249601941100761",
    "B-02": "120249615953090761",
}

# IDs obtidos no upload anterior (Parte 1)
IMG_HASH   = "dca3de87331093fb17803cb061ab8b07"   # SORTEIO-DRAGSTER.png
VIDEO_IDS  = [
    "2897389440619731",   # etapa 3-vid-01.mp4
    "2130921221187540",   # etapa 3-vid-02.mp4
    "910059035503249",    # etapa 3-vid-03.mp4
    "4513429778925528",   # etapa 3-vid-04.mp4
]

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

def load_env():
    for line in (Path.home() / ".adforge/.env").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

def _token(): return os.environ["META_ACCESS_TOKEN"]
def _base():  return f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}"
def _acct():  return os.environ["META_AD_ACCOUNT_ID"]

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

def log(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def make_creative():
    log("1. Criando creative sprint final RMKT...")
    asset_feed = {
        "images":                [{"hash": IMG_HASH}],
        "videos":                [{"video_id": vid} for vid in VIDEO_IDS],
        "bodies":                [{"text": t} for t in COPY_SPRINT["bodies"]],
        "titles":                [{"text": t} for t in COPY_SPRINT["titles"]],
        "call_to_action_types":  ["SHOP_NOW"],
        "link_urls":             [{"website_url": TICKET_URL}],
        "ad_formats":            ["AUTOMATIC_FORMAT"],
    }
    data = {
        "name":               "creative-3etapa-rmkt-sprint-final",
        "object_story_spec":  json.dumps({"page_id": PAGE_ID}),
        "asset_feed_spec":    json.dumps(asset_feed),
    }
    r, err = api_post(f"{_base()}/{_acct()}/adcreatives", data)
    if err:
        log(f"   ERRO creative: {err}")
        return None
    cid = r.get("id")
    log(f"   creative OK id={cid}")
    return cid

def create_ads(creative_id):
    log("2. Criando ads PAUSED em B-00, B-01, B-02...")
    results = []
    for label, adset_id in ADSETS.items():
        r, err = api_post(f"{_base()}/{_acct()}/ads", {
            "name":      f"[RMKT] 3aEtapa {label} SprintFinal | auto",
            "adset_id":  adset_id,
            "creative":  json.dumps({"creative_id": creative_id}),
            "status":    "PAUSED",
        })
        ok = bool(r and r.get("id"))
        log(f"   {label} → {'PAUSED ✓ id=' + r['id'] if ok else 'ERRO: ' + str(err)}")
        results.append((label, ok))
    return results

def main():
    load_env()
    log("=== Sprint Final — Creative + Ads ===")
    creative_id = make_creative()
    if not creative_id:
        sys.exit(1)
    results = create_ads(creative_id)
    ok = sum(1 for _, s in results if s)
    print(f"\nAds criados: {ok}/3 PAUSED — Renato ativa no Gerenciador.")

if __name__ == "__main__":
    main()
