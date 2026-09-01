import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

token = os.getenv('META_ACCESS_TOKEN')
ad_account = os.getenv('META_AD_ACCOUNT_ID')

url = f'https://graph.facebook.com/v25.0/{ad_account}/adsets?fields=id,name,status,effective_status,campaign{{name}}&limit=100&access_token={token}'
req = urllib.request.urlopen(url)
data = json.loads(req.read()).get('data', [])

print("ADSETS ATIVOS — 3ª Etapa:")
for a in data:
    camp = a.get('campaign', {}).get('name', '')
    if '3' not in camp and 'Etapa' not in camp and 'COPIA' not in camp.upper():
        continue
    status = a.get('effective_status', '')
    if status != 'ACTIVE':
        continue
    print(f"  ID={a['id']} | {a['name']}")

print("\nBUSCANDO ADS EXISTENTES:")
for a in data:
    camp = a.get('campaign', {}).get('name', '')
    if '3' not in camp and 'Etapa' not in camp and 'COPIA' not in camp.upper():
        continue
    status = a.get('effective_status', '')
    if status != 'ACTIVE':
        continue
    # buscar ads do adset
    ads_url = f"https://graph.facebook.com/v25.0/{a['id']}/ads?fields=id,name,status,creative{{id,object_story_spec,asset_feed_spec}},tracking_specs&access_token={token}"
    req2 = urllib.request.urlopen(ads_url)
    ads = json.loads(req2.read()).get('data', [])
    for ad in ads:
        print(f"  ADSET={a['name'][:40]} | AD_ID={ad['id']} | {ad['name'][:40]}")
        creative = ad.get('creative', {})
        print(f"    creative_id={creative.get('id')}")
