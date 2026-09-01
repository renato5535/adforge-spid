#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnóstico: por que o update de ad com criativo DCO falha?"""
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

# Ad que falhou + criativo DCO que foi criado
AD_ID  = '120249461304420761'
CID    = '979612601759839'

# 1) Ver estado atual do ad
r = requests.get(f'{BASE}/{AD_ID}', params={
    'fields': 'id,name,status,adset_id,creative{id,name,object_type}',
    'access_token': TOKEN
}).json()
print("=== AD ATUAL ===")
print(json.dumps(r, indent=2, ensure_ascii=False))

# 2) Ver o criativo DCO criado
r2 = requests.get(f'{BASE}/{CID}', params={
    'fields': 'id,name,object_type,asset_feed_spec,object_story_spec',
    'access_token': TOKEN
}).json()
print("\n=== CRIATIVO DCO ===")
print(json.dumps(r2, indent=2, ensure_ascii=False))

# 3) Tentar update com erro completo
r3 = requests.post(f'{BASE}/{AD_ID}', json={
    'creative': {'creative_id': CID},
    'access_token': TOKEN
}).json()
print("\n=== RESULTADO UPDATE ===")
print(json.dumps(r3, indent=2, ensure_ascii=False))
