from pathlib import Path
import os, json, urllib.request

for line in (Path.home() / '.adforge/.env').read_text(encoding='utf-8').splitlines():
    s = line.strip()
    if s and not s.startswith('#') and '=' in s:
        k, _, v = s.partition('=')
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

token   = os.environ['META_ACCESS_TOKEN']
ad_acct = os.environ['META_AD_ACCOUNT_ID']
base    = 'https://graph.facebook.com/v25.0'

url = f'{base}/{ad_acct}/adsets?fields=id,name,status,effective_status,campaign{{name}}&limit=200&access_token={token}'
req = urllib.request.urlopen(url, timeout=30)
data = json.loads(req.read()).get('data', [])

print('ADSETS 3a ETAPA (todos os status):')
for a in data:
    camp = a.get('campaign', {}).get('name', '')
    name = a.get('name', '')
    if ('3' not in camp and 'Etapa' not in camp and 'COPIA' not in camp.upper()
            and 'carrossel' not in name.lower()):
        continue
    status = a.get('effective_status', '?')
    print(f'  [{status[:6]}] id={a["id"]} | {name[:55]}')
    print(f'           camp: {camp[:55]}')
