#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige destination_type dos adsets: EVENT → WEBSITE
"""
import os, json, requests

env = {}
with open(os.path.expanduser('~/.adforge/.env')) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            env[k.strip()] = v.strip()

TOKEN = env['META_ACCESS_TOKEN']
VER   = 'v25.0'
BASE  = f'https://graph.facebook.com/{VER}'

ADSETS = [
    ('120249458543460761', 'A-02 Engajamento 365D'),
    ('120249458542640761', 'A-01 LKL 1% Purchase 180D'),
    ('120249458541220761', 'B-03 InitiateCheckout 180D'),
    ('120249458540310761', 'B-02 Purchase 180D'),
    ('120249458539200761', 'B-01 Video View 95% 180D'),
    ('120249458523540761', 'B-00 Pageview 180D'),
]

print("=== VERIFICANDO ADSETS ===\n")
for adset_id, name in ADSETS:
    r = requests.get(f'{BASE}/{adset_id}', params={
        'fields': 'id,name,destination_type,is_dynamic_creative,optimization_goal,billing_event',
        'access_token': TOKEN
    }).json()
    dst = r.get('destination_type', 'N/A')
    dco = r.get('is_dynamic_creative', False)
    print(f"  {name}")
    print(f"    destination_type: {dst}  |  DCO: {dco}")

    if dst != 'WEBSITE':
        upd = requests.post(f'{BASE}/{adset_id}', json={
            'destination_type': 'WEBSITE',
            'access_token': TOKEN
        }).json()
        if upd.get('success'):
            print(f"    ✅ Corrigido → WEBSITE")
        else:
            err = upd.get('error', {})
            print(f"    ❌ Erro: {err.get('error_user_msg') or err.get('message','?')}")
    else:
        print(f"    ✅ Já está WEBSITE")
    print()
