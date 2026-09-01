"""
Atualiza ads 3ª Etapa SPID Cup 2026:
- Upload das 3 artes Corvus
- Remove copies familia 2o lote (R$120)
- Adiciona copies familia 3o lote (R$135) + urgencia 15 dias
- PROSPECTO: adiciona FALTAM-15-DIAS + FAMILIA-PARA-2-PESSOAS
- RMKT: adiciona FALTAM-15-DIAS + COMPRA-SITE
- Ads ficam PAUSED para revisao do Renato
"""
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/.adforge/daily_analyst"))
from common import load_env, http_get_json, http_post_json
import urllib.request, urllib.parse, urllib.error

env   = load_env()
TOKEN = env.get("META_ACCESS_TOKEN", "")
VER   = env.get("META_API_VERSION", "v25.0")
ACCT  = env.get("META_AD_ACCOUNT_ID", "act_881694943239418")
BASE  = "https://graph.facebook.com/%s" % VER
PAGE_ID = "102560719007016"

IMAGE_FILES = {
    "FALTAM-15-DIAS": r"E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3\FALTAM-15-DIAS.png",
    "COMPRA-SITE":    r"E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3\COMPRA-SITE.png",
    "FAMILIA-2P":     r"E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3\FAMÍLIA - PARA 2 PESSOAS.png",
}

IMAGES_FOR = {
    "RMKT":      ["FALTAM-15-DIAS", "COMPRA-SITE"],
    "PROSPECTO": ["FALTAM-15-DIAS", "FAMILIA-2P"],
}

# Textos a remover (match normalizado)
BODIES_REMOVE = {
    "familia no spid cup: 2 pessoas por r$120 na arquibancada + box. obrigatorio documento de identificacao na retirada. 100 unidades, so online.",
    "traga a familia. r$120 garante 2 entradas na arquibancada + box. so online, 100 unidades. 3a etapa spid cup, 28/ago, itatiba.",
}
TITLES_REMOVE = {
    "familia - r$120 para 2 pessoas",
    "individual r$80 | familia r$120",
    "lote 1 esgotou - 2o lote aberto",
}

# Textos a adicionar
BODIES_ADD = [
    "Família no SPID Cup: 2 ingressos por R$135. Arquibancada + box, 3 dias de arrancada real. 28 a 30/Ago, Itatiba/SP.",
    "R$67,50 por pessoa. Traga quem você gosta pra pista de 201m, Pro Mod a 355km/h. SPID Cup 3ª Etapa, 28/Ago.",
    "Faltam 15 dias. Individual R$80, Família R$135. São Paulo International Dragway, 28 a 30/Ago, Itatiba/SP.",
]
TITLES_ADD = [
    "Família — R$135 para 2 pessoas",
    "Individual R$80 | Família R$135",
    "Faltam 15 dias — garanta agora",
]


def norm(text):
    return text.strip().lower()


def upload_image(name, path):
    """Upload imagem e retorna hash. name = stem do arquivo."""
    with open(path, "rb") as f:
        img_data = f.read()
    boundary = "AdForgeBoundary20260813"
    filename  = os.path.basename(path)
    part = (
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
        "Content-Type: image/png\r\n\r\n" % (boundary, name, filename)
    ).encode("utf-8") + img_data + ("\r\n--%s--\r\n" % boundary).encode("utf-8")
    url = "%s/%s/adimages?access_token=%s" % (BASE, ACCT, TOKEN)
    req = urllib.request.Request(
        url, data=part,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary,
                 "User-Agent": "adforge/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read().decode("utf-8"))
            images = resp.get("images") or {}
            for _fn, info in images.items():
                return info.get("hash")
    except urllib.error.HTTPError as e:
        print("  UPLOAD HTTP %s: %s" % (e.code, e.read().decode("utf-8","replace")[:300]))
        return None
    except Exception as ex:
        print("  UPLOAD EX:", ex)
        return None


def api_get(path, params=None):
    p = dict(params or {})
    p["access_token"] = TOKEN
    data, err = http_get_json(BASE + path, p)
    return data, err


def api_post(path, payload):
    payload = dict(payload)
    payload["access_token"] = TOKEN
    body = urllib.parse.urlencode(payload).encode("utf-8")
    req  = urllib.request.Request(
        BASE + path, data=body,
        headers={"User-Agent": "adforge/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            b = json.loads(e.read().decode("utf-8"))
        except Exception:
            b = {"raw": e.read().decode("utf-8","replace")[:400]}
        return b, "HTTP %s" % e.code
    except Exception as ex:
        return None, str(ex)


# ──────────────────────────────
print("=== ETAPA 1: Upload das 3 imagens ===")
hashes = {}
for name, path in IMAGE_FILES.items():
    if not os.path.exists(path):
        print("  [SKIP] arquivo não encontrado: %s" % path)
        continue
    print("  Uploading %s ..." % name, end=" ", flush=True)
    h = upload_image(name, path)
    if h:
        hashes[name] = h
        print("OK hash=...%s" % h[-6:])
    else:
        print("FALHOU")

print("\n=== ETAPA 2: Buscar ads ativos ===")
data, err = api_get("/%s/ads" % ACCT, {
    "fields": "id,name,effective_status,creative{id,asset_feed_spec},adset{name,campaign{name}}",
    "filtering": json.dumps([
        {"field": "effective_status", "operator": "IN",  "value": ["ACTIVE", "IN_PROCESS"]},
        {"field": "campaign.name",    "operator": "CONTAIN", "value": "3ª Etapa"},
    ]),
    "limit": "50",
})
if err:
    print("ERRO buscar ads:", err)
    sys.exit(1)

ads = data.get("data", [])
print("Ads ativos encontrados: %d\n" % len(ads))

results = []

for ad in ads:
    ad_id   = ad["id"]
    ad_name = ad.get("name", "?")
    camp    = ((ad.get("adset") or {}).get("campaign") or {}).get("name", "?")
    ct      = "RMKT" if "RMKT" in camp else "PROSPECTO"
    cr      = ad.get("creative") or {}
    cr_id   = cr.get("id")
    spec    = cr.get("asset_feed_spec") or {}

    print("--- %s [%s] (cr=%s) ---" % (ad_name, ct, cr_id))

    old_bodies = spec.get("bodies") or []
    old_titles = spec.get("titles") or []
    old_images = spec.get("images") or []

    # Filtra bodies
    new_bodies = [b for b in old_bodies if norm(b.get("text","")) not in BODIES_REMOVE]
    rm_b = len(old_bodies) - len(new_bodies)
    exist_b = {norm(b.get("text","")) for b in new_bodies}
    for txt in BODIES_ADD:
        if norm(txt) not in exist_b:
            new_bodies.append({"text": txt})

    # Filtra titles
    new_titles = [t for t in old_titles if norm(t.get("text","")) not in TITLES_REMOVE]
    rm_t = len(old_titles) - len(new_titles)
    exist_t = {norm(t.get("text","")) for t in new_titles}
    for txt in TITLES_ADD:
        if norm(txt) not in exist_t:
            new_titles.append({"text": txt})

    # Adiciona imagens novas
    new_images  = list(old_images)
    exist_hashes = {img.get("hash") for img in new_images}
    added_imgs = []
    for img_key in IMAGES_FOR.get(ct, []):
        h = hashes.get(img_key)
        if h and h not in exist_hashes:
            new_images.append({"hash": h})
            exist_hashes.add(h)
            added_imgs.append(img_key)

    print("  bodies : %d → -%d +%d = %d" % (len(old_bodies), rm_b, len(BODIES_ADD), len(new_bodies)))
    print("  titles : %d → -%d +%d = %d" % (len(old_titles), rm_t, len(TITLES_ADD), len(new_titles)))
    print("  images : %d + %d novos = %d" % (len(old_images), len(added_imgs), len(new_images)))

    # Monta spec atualizado preservando todos os outros campos
    new_spec = dict(spec)
    new_spec["bodies"]  = new_bodies
    new_spec["titles"]  = new_titles
    new_spec["images"]  = new_images
    new_spec.pop("degrees_of_freedom_spec", None)

    # Cria novo criativo
    cr_payload = {
        "name": "3aEtapa-f3lote-%s" % ad_id,
        "object_story_spec": json.dumps({"page_id": PAGE_ID}),
        "asset_feed_spec":   json.dumps(new_spec),
    }
    cr_resp, cr_err = api_post("/%s/adcreatives" % ACCT, cr_payload)

    if cr_err or not (cr_resp or {}).get("id"):
        print("  ERRO criativo: %s → %s" % (cr_err, str(cr_resp)[:300]))
        results.append({"ad": ad_name, "ct": ct, "status": "ERRO_CR", "detail": str(cr_resp)[:200]})
        continue

    new_cr_id = cr_resp["id"]
    print("  novo cr: %s" % new_cr_id)

    # Patcha o ad (sem status — fica PAUSED)
    patch_resp, patch_err = api_post("/%s" % ad_id, {
        "creative": json.dumps({"creative_id": new_cr_id}),
    })

    if patch_err:
        print("  ERRO patch: %s → %s" % (patch_err, str(patch_resp)[:300]))
        results.append({"ad": ad_name, "ct": ct, "status": "ERRO_PATCH", "detail": str(patch_resp)[:200]})
    else:
        ok = patch_resp.get("success") or patch_resp.get("id")
        print("  PATCH OK ✓" if ok else "  PATCH resp: %s" % patch_resp)
        results.append({"ad": ad_name, "ct": ct, "status": "OK", "new_cr": new_cr_id})

print("\n=== RESUMO FINAL ===")
ok_count = sum(1 for r in results if r["status"] == "OK")
for r in results:
    icon = "✓" if r["status"] == "OK" else "✗"
    print("[%s] [%s] %s  %s" % (icon, r.get("ct","?"), r.get("ad","?"), r.get("new_cr", r.get("detail",""))))
print("\n%d/%d atualizados com sucesso." % (ok_count, len(results)))
print("Ads estão PAUSED — ative manualmente no Meta Ads Manager.")
