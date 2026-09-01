#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, requests

env = {}
with open(os.path.expanduser('~/.adforge/.env')) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            env[k.strip()] = v.strip()

TOKEN = env['TELEGRAM_BOT_TOKEN']
CHAT  = env['TELEGRAM_CHAT_ID']

msg = (
    "✅ Ads 3ª Etapa SPID Cup — ATUALIZADOS\n\n"
    "DCO aplicado: 36/36 ads ✅\n"
    "Destino corrigido: 6/6 adsets → Site ✅\n"
    "CTA: Comprar agora ✅\n"
    "Copies: 5 textos + 5 títulos por ad ✅\n\n"
    "Ambas as campanhas continuam PAUSADAS.\n"
    "Revise no Ads Manager e ative quando quiser."
)

r = requests.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage', json={
    'chat_id': CHAT,
    'text': msg,
})
print(r.status_code, r.json().get('ok'))
