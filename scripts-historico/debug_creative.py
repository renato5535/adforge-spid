"""Debug creative — mostra erro completo do Meta."""
import os, json, urllib.request, urllib.parse
from pathlib import Path

def load_env():
    for line in (Path.home() / ".adforge/.env").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

load_env()
TOKEN = os.environ["META_ACCESS_TOKEN"]
VER   = os.environ.get("META_API_VERSION", "v25.0")
ACCT  = os.environ["META_AD_ACCOUNT_ID"]
BASE  = f"https://graph.facebook.com/{VER}"
PAGE  = "102560719007016"
URL   = "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"

IMG_HASH  = "b20e0fac2793c8edee81b78c61ab8b07"
VIDEO_IDS = ["2897389440619731", "2130921221187540", "910059035503249", "4513429778925528"]

asset_feed = {
    "images":               [{"hash": IMG_HASH}],
    "videos":               [{"video_id": vid} for vid in VIDEO_IDS],
    "bodies":               [{"text": "Quem hesitou: queimou. Individual R$90, Família R$135. SPID Cup 3ª Etapa — 28 a 30/Ago, Itatiba."}],
    "titles":               [{"text": "3ª Etapa SPID Cup — 28/Ago"}],
    "call_to_action_types": ["SHOP_NOW"],
    "link_urls":            [{"website_url": URL}],
    "ad_formats":           ["AUTOMATIC_FORMAT"],
}

data = {
    "name":              "debug-creative-test",
    "object_story_spec": json.dumps({"page_id": PAGE}),
    "asset_feed_spec":   json.dumps(asset_feed),
    "access_token":      TOKEN,
}

encoded = urllib.parse.urlencode(data).encode()
req = urllib.request.Request(f"{BASE}/{ACCT}/adcreatives", data=encoded, method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
        print("OK:", resp)
except urllib.error.HTTPError as e:
    err = json.loads(e.read())
    print("ERRO COMPLETO:")
    print(json.dumps(err, indent=2, ensure_ascii=False))
