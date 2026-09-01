import os, json, urllib.request, urllib.parse
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

token = os.getenv('META_ACCESS_TOKEN')
ad_account = os.getenv('META_AD_ACCOUNT_ID')

print("=" * 65)
print("PAINEL AO VIVO — 3ª ETAPA SPID CUP 2026")
print("=" * 65)

# --- SALDO ---
url = f'https://graph.facebook.com/v25.0/{ad_account}?fields=funding_source_details,amount_spent&access_token={token}'
req = urllib.request.urlopen(url)
d = json.loads(req.read())
fsd = d.get('funding_source_details', {})
saldo = fsd.get('display_string', 'N/A')
gasto_total_cents = int(d.get('amount_spent', 0))
print(f"\nSaldo disponivel: {saldo}")

# --- INSIGHTS DE HOJE ---
url = f'https://graph.facebook.com/v25.0/{ad_account}/insights?fields=spend,purchase_roas,actions,action_values,impressions,clicks,reach&date_preset=today&level=account&access_token={token}'
req = urllib.request.urlopen(url)
ins = json.loads(req.read()).get('data', [{}])[0]
spend_hoje = float(ins.get('spend', 0))
roas_list = ins.get('purchase_roas', [])
roas_hoje = float(roas_list[0]['value']) if roas_list else 0.0
actions = ins.get('actions', [])
purchases_hoje = next((int(a['value']) for a in actions if a['action_type'] == 'purchase'), 0)
av = ins.get('action_values', [])
receita_hoje = float(next((a['value'] for a in av if a['action_type'] == 'purchase'), 0))
impressoes = int(ins.get('impressions', 0))
cliques = int(ins.get('clicks', 0))
alcance = int(ins.get('reach', 0))

print(f"\n--- HOJE ---")
print(f"  Gasto:      R${spend_hoje:.2f}")
print(f"  Receita:    R${receita_hoje:.2f}")
print(f"  ROAS:       {roas_hoje:.2f}x")
print(f"  Compras:    {purchases_hoje}")
print(f"  Impressoes: {impressoes:,}")
print(f"  Alcance:    {alcance:,}")
print(f"  Cliques:    {cliques:,}")

# --- INSIGHTS PERIODO (desde lancamento) ---
url = f'https://graph.facebook.com/v25.0/{ad_account}/insights?fields=spend,purchase_roas,actions,action_values&date_preset=this_year&level=account&access_token={token}'
req = urllib.request.urlopen(url)
ins2 = json.loads(req.read()).get('data', [{}])[0]
spend_total = float(ins2.get('spend', 0))
roas_list2 = ins2.get('purchase_roas', [])
roas_total = float(roas_list2[0]['value']) if roas_list2 else 0.0
av2 = ins2.get('action_values', [])
receita_total = float(next((a['value'] for a in av2 if a['action_type'] == 'purchase'), 0))
actions2 = ins2.get('actions', [])
purchases_total = next((int(a['value']) for a in actions2 if a['action_type'] == 'purchase'), 0)

print(f"\n--- ANO (acumulado) ---")
print(f"  Gasto:      R${spend_total:.2f}")
print(f"  Receita:    R${receita_total:.2f}")
print(f"  ROAS:       {roas_total:.2f}x")
print(f"  Compras:    {purchases_total}")

# --- ADSETS ATIVOS ---
print(f"\n--- ADSETS ATIVOS (3ª Etapa) ---")
url = f'https://graph.facebook.com/v25.0/{ad_account}/adsets?fields=id,name,status,effective_status,campaign{{name}},daily_budget,lifetime_budget,budget_remaining,insights{{spend,purchase_roas,actions,impressions}}&date_preset=today&limit=100&access_token={token}'
req = urllib.request.urlopen(url)
adsets = json.loads(req.read()).get('data', [])

for a in adsets:
    camp_name = a.get('campaign', {}).get('name', '?')
    if '3' not in camp_name and 'Etapa' not in camp_name and 'COPIA' not in camp_name.upper():
        continue
    status = a.get('effective_status', '?')
    if status not in ('ACTIVE', 'CAMPAIGN_PAUSED', 'PAUSED'):
        continue
    name = a.get('name', '?')[:55]
    lb = a.get('lifetime_budget', '')
    db = a.get('daily_budget', '')
    br = a.get('budget_remaining', '')
    if lb:
        budget_str = f"LT R${int(lb)/100:.0f} | restam R${int(br)/100:.0f}"
    elif db:
        budget_str = f"DAILY R${int(db)/100:.0f}"
    else:
        budget_str = "CBO"
    insights = a.get('insights', {}).get('data', [{}])[0] if a.get('insights') else {}
    spend = float(insights.get('spend', 0))
    roas_list = insights.get('purchase_roas', [])
    roas = float(roas_list[0]['value']) if roas_list else 0.0
    actions_a = insights.get('actions', [])
    purchases = next((int(x['value']) for x in actions_a if x['action_type'] == 'purchase'), 0)
    emoji = "🟢" if status == 'ACTIVE' else "🔴"
    print(f"\n  {emoji} [{status[:4]}] {name}")
    print(f"     camp: {camp_name[:55]}")
    print(f"     budget: {budget_str}")
    if spend > 0:
        print(f"     hoje:  R${spend:.2f} gasto | ROAS {roas:.1f}x | {purchases} compras")
    else:
        print(f"     hoje:  sem gasto registrado")

print("\n" + "=" * 65)
