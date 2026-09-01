import urllib.request, urllib.parse, json, os
from pathlib import Path
from datetime import date

env_file = Path.home() / ".adforge" / ".env"
for line in env_file.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip("'\""))

TOKEN    = os.environ["META_ACCESS_TOKEN"]
ACCOUNT  = os.environ["META_AD_ACCOUNT_ID"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT  = os.environ["TELEGRAM_CHAT_ID"]
TODAY    = date.today().isoformat()

def get(path, params):
    params["access_token"] = TOKEN
    url = "https://graph.facebook.com/v25.0/" + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())

def tg_send(msg):
    data = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=data)
    urllib.request.urlopen(req, timeout=10)

# Verifica adsets ativos
adsets = get(ACCOUNT + "/adsets", {
    "effective_status": json.dumps(["ACTIVE"]),
    "fields": "id,name",
    "limit": 20
})

linhas = []
total_spend = 0.0
algum_com_entrega = False

for a in adsets.get("data", []):
    ins = get(a["id"] + "/insights", {
        "time_range": json.dumps({"since": TODAY, "until": TODAY}),
        "fields": "spend,impressions"
    })
    r = (ins.get("data") or [{}])[0]
    sp  = float(r.get("spend", 0))
    imp = int(r.get("impressions", 0))
    total_spend += sp
    flag = "✅" if sp > 0 else "❌"
    if sp > 0:
        algum_com_entrega = True
    linhas.append(f"{flag} {a['name'][:35]} | R${sp:.2f} | {imp} imp")

if algum_com_entrega:
    status = "✅ <b>ENTREGANDO</b> — reset funcionou!"
else:
    status = "❌ <b>AINDA SEM ENTREGA</b> — verifique manualmente"

msg = f"""🔍 <b>Check 3ª Etapa SPID Cup — {TODAY}</b>

{status}

<b>Adsets:</b>
""" + "\n".join(linhas) + f"""

<b>Total spend hoje: R${total_spend:.2f}</b>"""

tg_send(msg)
print(msg)
