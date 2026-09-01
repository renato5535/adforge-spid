"""
Tenta criar 3 adsets de carrossel na campanha RMKT da 3a Etapa.
Se der subcode 3858634, reporta e dá instrucoes para UI.
"""
from pathlib import Path
import os, json, urllib.request, urllib.parse, urllib.error

for line in (Path.home() / '.adforge/.env').read_text(encoding='utf-8').splitlines():
    s = line.strip()
    if s and not s.startswith('#') and '=' in s:
        k, _, v = s.partition('=')
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TOKEN   = os.environ['META_ACCESS_TOKEN']
AD_ACCT = os.environ['META_AD_ACCOUNT_ID']
BASE    = f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}"
PIXEL   = '867066736318670'

# ── 1. Pegar ID da campanha RMKT ────────────────────────────────────────────
print('1. Buscando campanha RMKT 3a Etapa...')
url = f'{BASE}/{AD_ACCT}/campaigns?fields=id,name,effective_status&limit=50&access_token={TOKEN}'
req = urllib.request.urlopen(url, timeout=20)
camps = json.loads(req.read()).get('data', [])

rmkt_camp_id = None
for c in camps:
    if 'RMKT' in c['name'] and '3' in c['name'] and 'Etapa' in c['name'] and 'COPIA' in c['name'].upper():
        rmkt_camp_id = c['id']
        print(f'   Encontrada: {c["name"]}')
        print(f'   ID: {rmkt_camp_id} | Status: {c["effective_status"]}')
        break

if not rmkt_camp_id:
    print('   ERRO: campanha RMKT nao encontrada')
    exit(1)

# ── 2. Pegar targeting do B-00 (base para copiar) ───────────────────────────
print('\n2. Buscando targeting do B-00 como base...')
url2 = f'{BASE}/120249615946860761?fields=targeting,optimization_goal,billing_event,bid_strategy,destination_type&access_token={TOKEN}'
req2 = urllib.request.urlopen(url2, timeout=20)
b00 = json.loads(req2.read())
targeting = b00.get('targeting', {})
opt_goal   = b00.get('optimization_goal', 'OFFSITE_CONVERSIONS')
billing    = b00.get('billing_event', 'IMPRESSIONS')
dest_type  = b00.get('destination_type', 'WEBSITE')
print(f'   opt_goal={opt_goal} | billing={billing} | dest={dest_type}')

# ── 3. Tentar criar adset de carrossel ──────────────────────────────────────
print('\n3. Tentando criar adset B-C1 Carrossel V1 (PAUSED)...')

adset_payload = {
    'name':               'B-C1 Carrossel Atrações V1 — 3ª Etapa',
    'campaign_id':        rmkt_camp_id,
    'status':             'PAUSED',
    'optimization_goal':  opt_goal,
    'billing_event':      billing,
    'destination_type':   dest_type,
    'targeting':          json.dumps(targeting),
    'promoted_object':    json.dumps({'pixel_id': PIXEL, 'custom_event_type': 'PURCHASE'}),
    # RMKT encerra domingo 30/Ago 11h BRT = 14h UTC (regra estabelecida)
    'time_stop':          '2026-08-30T14:00:00+0000',
    'access_token':       TOKEN,
}

data = urllib.parse.urlencode(adset_payload).encode()
req3 = urllib.request.Request(f'{BASE}/{AD_ACCT}/adsets', data=data, method='POST')
try:
    resp3 = urllib.request.urlopen(req3, timeout=30)
    result = json.loads(resp3.read())
    adset_id = result.get('id')
    print(f'   OK! adset_id={adset_id}')
    print('\nCRIACAO VIA API FUNCIONOU — pode prosseguir com upload do carrossel.')
except urllib.error.HTTPError as e:
    err = json.loads(e.read())
    code = err.get('error', {}).get('code')
    subcode = err.get('error', {}).get('error_subcode')
    msg = err.get('error', {}).get('message', '')
    print(f'   BLOQUEADO — code={code} | subcode={subcode}')
    print(f'   msg: {msg}')
    if subcode == 3858634 or subcode == 3858504:
        print("""
API bloqueou criacao de adsets nesta campanha CBO.
INSTRUCOES PARA O RENATO (5 min no Gerenciador):

Campanha: [RMKT][CONVERSAO] 3a Etapa SPID Cup 2026 [COPIA]

Criar 3 conjuntos PAUSED com essas configuracoes:
  Nome:         B-C1 Carrossel Atracoes V1
  Nome:         B-C2 Carrossel Atracoes V2
  Nome:         B-C3 Carrossel Atracoes V3
  Objetivo:     Conversao — Compra
  Publico:      mesmo do B-00 (Pageview 180D)
  Posicionamentos: Automatico
  Orcamento:    sem budget proprio (CBO ja controla)
  Status:       PAUSED

Depois me passa os 3 IDs que eu subo os criativos automaticamente.
""")
    else:
        print(f'\n   Erro inesperado: {json.dumps(err, indent=2)}')
