"""Lista todos os adsets da campanha RMKT 3a Etapa para encontrar os novos."""
from pathlib import Path
import os, json, urllib.request, urllib.parse, time

for line in (Path.home() / '.adforge/.env').read_text(encoding='utf-8').splitlines():
    s = line.strip()
    if s and not s.startswith('#') and '=' in s:
        k, _, v = s.partition('=')
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TOKEN  = os.environ['META_ACCESS_TOKEN']
BASE   = f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}"
CAMP_ID = '120249601416320761'  # [RMKT] 3a Etapa SPID Cup 2026 [COPIA]

url = f'{BASE}/{CAMP_ID}/adsets?fields=id,name,status,effective_status,created_time&limit=50&access_token={TOKEN}'
with urllib.request.urlopen(url, timeout=20) as r:
    data = json.loads(r.read()).get('data', [])

print(f'Adsets na campanha RMKT ({len(data)} total):')
for a in sorted(data, key=lambda x: x.get('created_time',''), reverse=True):
    print(f'  [{a["effective_status"][:5]}] id={a["id"]} | {a["name"][:55]} | criado={a.get("created_time","?")}')
