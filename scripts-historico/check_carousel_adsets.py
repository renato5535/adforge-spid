"""Busca adsets com 'carrossel' no nome ou adsets PAUSED da 3a Etapa."""
import os, sys, json, urllib.request, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daily_analyst'))
from common import load_env
load_env()

token    = os.environ['META_ACCESS_TOKEN']
ad_acct  = os.environ['META_AD_ACCOUNT_ID']
base     = f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}"

url = f"{base}/{ad_acct}/adsets?fields=id,name,status,effective_status,campaign{{name}},targeting,optimization_goal&limit=200&access_token={token}"
req = urllib.request.urlopen(url, timeout=30)
data = json.loads(req.read()).get('data', [])

print("ADSETS 3ª ETAPA (todos os status):")
for a in data:
    camp = a.get('campaign', {}).get('name', '')
    if '3' not in camp and 'Etapa' not in camp and 'COPIA' not in camp.upper() and 'carrossel' not in a['name'].lower():
        continue
    status = a.get('effective_status', '?')
    print(f"  [{status[:4]}] id={a['id']} | {a['name'][:55]}")
    print(f"         camp: {camp[:55]}")
