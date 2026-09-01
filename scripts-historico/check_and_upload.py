"""
1. Verifica se os adsets novos existem na conta
2. Sobe as 3 imagens restantes e lista todos os hashes
"""
from pathlib import Path
import os, json, urllib.request, urllib.parse, urllib.error, time

for line in (Path.home() / '.adforge/.env').read_text(encoding='utf-8').splitlines():
    s = line.strip()
    if s and not s.startswith('#') and '=' in s:
        k, _, v = s.partition('=')
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TOKEN   = os.environ['META_ACCESS_TOKEN']
AD_ACCT = os.environ['META_AD_ACCOUNT_ID']
BASE    = f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}"

NOVOS_IDS = ['120250369010670761', '120250369008810761', '120250369014200761']
CAROUSEL_DIR = Path(r'E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3\carrossel-atrações')
PENDENTES    = ['PROMODS.png', 'RECREAÇÃO-INFANTIL.png', 'SORTEIO-EXCLUSIVO.png']

def log(msg): print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)

# ── 1. Verificar adsets ───────────────────────────────────────────────────────
log('=== Verificando adsets novos ===')
for aid in NOVOS_IDS:
    url = f'{BASE}/{aid}?fields=id,name,status,effective_status,account_id&access_token={TOKEN}'
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            d = json.loads(r.read())
            log(f'  OK  {aid} → {d.get("name")} | {d.get("effective_status")} | acct={d.get("account_id")}')
    except urllib.error.HTTPError as e:
        err = json.loads(e.read()).get('error', {})
        log(f'  ERR {aid}: {err.get("message")} (sub={err.get("error_subcode")})')

# ── 2. Listar imagens já subidas na conta ────────────────────────────────────
log('\n=== Buscando hashes já existentes na conta ===')
url2 = f'{BASE}/{AD_ACCT}/adimages?fields=hash,name,created_time&limit=100&access_token={TOKEN}'
with urllib.request.urlopen(url2, timeout=20) as r:
    imgs = json.loads(r.read()).get('data', [])

carousel_names = [p.stem for p in CAROUSEL_DIR.glob('*.png')]
hash_map = {}
for img in imgs:
    name = img.get('name', '')
    h    = img.get('hash', '')
    stem = name.replace('.png', '').replace('.jpg', '')
    if stem in carousel_names:
        # reconstrói nome com extensão
        fname = stem + '.png'
        hash_map[fname] = h
        log(f'  JA EXISTE: {fname} → {h}')

log(f'  {len(hash_map)}/11 hashes encontrados na conta')
faltam = [p for p in CAROUSEL_DIR.glob('*.png') if p.name not in hash_map]
log(f'  Precisam upload: {[p.name for p in faltam]}')

# ── 3. Upload das pendentes ───────────────────────────────────────────────────
if faltam:
    log('\n=== Upload das imagens pendentes ===')
    for fpath in faltam:
        stem = fpath.stem
        name = fpath.name
        img  = fpath.read_bytes()
        bnd  = '----MetaBnd'
        body = (f'--{bnd}\r\nContent-Disposition: form-data; name="{stem}"; '
                f'filename="{name}"\r\nContent-Type: image/png\r\n\r\n').encode() \
               + img + f'\r\n--{bnd}--\r\n'.encode()
        url3 = f'{BASE}/{AD_ACCT}/adimages?access_token={TOKEN}'
        req  = urllib.request.Request(url3, data=body, method='POST')
        req.add_header('Content-Type', f'multipart/form-data; boundary={bnd}')
        try:
            with urllib.request.urlopen(req, timeout=120) as r3:
                resp = json.loads(r3.read())
            for _, v in resp.get('images', {}).items():
                h = v.get('hash')
                hash_map[name] = h
                log(f'  UP OK  {name} → {h}')
        except urllib.error.HTTPError as e:
            log(f'  ERR {name}: {json.loads(e.read()).get("error",{}).get("message")}')

log(f'\n=== HASHES FINAIS ({len(hash_map)}/11) ===')
for k, v in sorted(hash_map.items()):
    print(f'  {k}: {v}')

# Salvar em arquivo para usar no próximo script
out = Path.home() / '.adforge' / 'carousel_hashes.json'
out.write_text(json.dumps(hash_map, ensure_ascii=False, indent=2), encoding='utf-8')
log(f'\nHashes salvos em {out}')
