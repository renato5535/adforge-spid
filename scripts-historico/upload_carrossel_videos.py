"""
Upload Carrossel + Vídeos — 3ª Etapa SPID Cup 2026
====================================================
1. Upload vid-04 (novo) + vid-05  →  IDs Meta
2. PATCH creative RMKT (2106004863658174) adicionando os 2 novos vídeos
3. Upload 11 imagens do carrossel-atrações
4. Cria 3 creatives de carrossel (V1/V2/V3 com capas diferentes)
5. Cria 3 ads carrossel PAUSED (1 por adset RMKT ativo)
"""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

ASSETS_DIR   = Path(r"E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3")
CAROUSEL_DIR = ASSETS_DIR / "carrossel-atrações"
TICKET_URL   = "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"
PAGE_ID      = "102560719007016"
PIXEL_ID     = "867066736318670"

CREATIVE_RMKT  = "2106004863658174"
EXISTING_VIDS  = ["2897389440619731", "910059035503249", "2130921221187540", "4513429778925528"]
EXISTING_IMG   = "dca3de87331093fb17803cb061ab8b07"

ADSETS = {
    "B-00": "120249615946860761",
    "B-01": "120249601941100761",
    "B-02": "120249615953090761",
}

# IDs dos ads ativos (para PATCH inline com novos vídeos)
ADS_RMKT = {
    "B-02": "120249615981500761",
    "B-00": "120249615979300761",
    "B-01": "120249601960410761",
}

NOVOS_VIDEOS = [
    ("etapa 3-vid-04.mp4", "[RMKT] Sprint Final v04-novo — 3ª Etapa SPID Cup"),
    ("etapa 3-vid-05.mp4", "[RMKT] Sprint Final v05 — 3ª Etapa SPID Cup"),
]

# Ordem base das 11 imagens (após a capa)
IMAGENS_BASE = [
    "OS-CARROS.png",
    "AÇÕES.png",
    "ACESSO-LIVRE.png",
    "DUAS-PRAÇAS.png",
    "FESTIVAL-DO-CHURRASCO.png",
    "LOJAS.png",
    "LOUNGE.png",
    "RECREAÇÃO-INFANTIL.png",
    "CRIANÇAS.png",
]

# Títulos por card
CARD_TITLES = {
    "PROMODS.png":              "Pro Mod a 355km/h",
    "OS-CARROS.png":            "Os carros mais rápidos do Brasil",
    "AÇÕES.png":                "Ação ao vivo na pista",
    "ACESSO-LIVRE.png":         "Acesso livre ao paddock",
    "DUAS-PRAÇAS.png":          "Duas praças de alimentação",
    "FESTIVAL-DO-CHURRASCO.png":"Festival do Churrasco",
    "LOJAS.png":                "Lojas e expositores",
    "LOUNGE.png":               "Lounge exclusivo",
    "RECREAÇÃO-INFANTIL.png":   "Recreação infantil",
    "CRIANÇAS.png":             "Diversão para toda a família",
    "SORTEIO-EXCLUSIVO.png":    "Sorteio exclusivo no evento",
}

# Meta limita carrossel a 10 cards — cada variação tem 1 capa + 9 resto = 10 total
# V1: capa PROMODS, drop CRIANÇAS
# V2: capa SORTEIO-EXCLUSIVO, drop LOJAS
# V3: capa FESTIVAL-DO-CHURRASCO, drop RECREAÇÃO-INFANTIL
VARIACOES = [
    ("V1", "PROMODS.png", [
        "OS-CARROS.png", "AÇÕES.png", "ACESSO-LIVRE.png", "DUAS-PRAÇAS.png",
        "FESTIVAL-DO-CHURRASCO.png", "LOJAS.png", "LOUNGE.png",
        "RECREAÇÃO-INFANTIL.png", "SORTEIO-EXCLUSIVO.png",
    ]),
    ("V2", "SORTEIO-EXCLUSIVO.png", [
        "PROMODS.png", "OS-CARROS.png", "AÇÕES.png", "ACESSO-LIVRE.png",
        "DUAS-PRAÇAS.png", "FESTIVAL-DO-CHURRASCO.png", "LOUNGE.png",
        "RECREAÇÃO-INFANTIL.png", "CRIANÇAS.png",
    ]),
    ("V3", "FESTIVAL-DO-CHURRASCO.png", [
        "PROMODS.png", "OS-CARROS.png", "AÇÕES.png", "ACESSO-LIVRE.png",
        "DUAS-PRAÇAS.png", "LOJAS.png", "LOUNGE.png",
        "CRIANÇAS.png", "SORTEIO-EXCLUSIVO.png",
    ]),
]

# Adset destino de cada variação (mais saturado primeiro)
VARIACOES_ADSET = {
    "V1": "B-02",  # freq 25.5 — mais saturado
    "V2": "B-00",  # freq 16.4
    "V3": "B-01",  # freq 9.8
}

COPY_RMKT = {
    "bodies": [
        "Quem hesitou: queimou. Individual R$90, Família R$135. SPID Cup 3ª Etapa — 28 a 30/Ago, São Paulo International Dragway, Itatiba.",
        "Borrachão feito, pista quente. Faltam 8 dias pra largada. Individual R$90, Família R$135 — garanta agora em agendaesportiva.com.br.",
        "Você viu o SPID. Faltam 8 dias. Individual R$90, Família R$135. 28/Ago ao vivo — arrancada real de 201m, carros a 355km/h.",
        "201m de pista. Pro Mod a 355km/h. 28/Ago ao vivo. Só existe ao vivo — Individual R$90. São Paulo International Dragway, Itatiba/SP.",
        "Volta pra pista. 3ª Etapa SPID Cup — 28 a 30/Ago, Itatiba. Individual R$90, Família R$135. Não existe câmera lenta ao vivo.",
    ],
    "titles": [
        "3ª Etapa SPID Cup — 28/Ago",
        "Individual R$90 | Família R$135",
        "Faltam 8 dias — garanta agora",
        "São Paulo International Dragway",
        "28–30/Ago | Itatiba/SP",
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_env():
    for line in (Path.home() / ".adforge/.env").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

def _token():  return os.environ["META_ACCESS_TOKEN"]
def _base():   return f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}"
def _acct():   return os.environ["META_AD_ACCOUNT_ID"]

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def api_get(url, params=None):
    params = {**(params or {}), "access_token": _token()}
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=30) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, json.loads(e.read()).get("error", {}).get("message", str(e))

def api_post(url, data):
    data = {**data, "access_token": _token()}
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, json.loads(e.read()).get("error", {}).get("message", str(e))

# ── 1. Upload vídeo (chunked) ─────────────────────────────────────────────────

def upload_video(filepath, title):
    fpath = Path(filepath)
    fsize = fpath.stat().st_size
    log(f"  Upload vídeo: {fpath.name} ({fsize/1024/1024:.1f} MB)")

    r, err = api_post(f"{_base()}/{_acct()}/advideos", {
        "upload_phase": "start", "file_size": fsize, "title": title,
    })
    if err:
        log(f"  ERRO start: {err}"); return None
    session_id = r.get("upload_session_id")
    video_id   = r.get("video_id")

    chunk_size = 5 * 1024 * 1024
    token = _token()
    with open(fpath, "rb") as f:
        offset = 0
        while True:
            chunk = f.read(chunk_size)
            if not chunk: break
            boundary = "----VideoBnd"
            body = (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"upload_phase\"\r\n\r\ntransfer\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"upload_session_id\"\r\n\r\n{session_id}\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"start_offset\"\r\n\r\n{offset}\r\n"
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"video_file_chunk\"; filename=\"{fpath.name}\"\r\nContent-Type: video/mp4\r\n\r\n"
            ).encode() + chunk + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(f"{_base()}/{_acct()}/advideos", data=body, method="POST")
            req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
            req.add_header("Authorization", f"Bearer {token}")
            try:
                with urllib.request.urlopen(req, timeout=120) as r2:
                    json.loads(r2.read())
            except urllib.error.HTTPError as e:
                log(f"  ERRO chunk @{offset}: {json.loads(e.read()).get('error',{}).get('message')}")
                return None
            offset += len(chunk)
            print(f"  {int(offset/fsize*100)}% ({offset//1024//1024}MB)    ", end="\r")

    r3, err3 = api_post(f"{_base()}/{_acct()}/advideos", {
        "upload_phase": "finish", "upload_session_id": session_id, "title": title,
    })
    if err3:
        log(f"  ERRO finish: {err3}"); return None
    log(f"  vídeo OK id={video_id}")
    return video_id

# ── 2. PATCH inline nos ads RMKT (não no creative — Meta não permite editar creative em uso) ──

def patch_ads_add_videos(new_video_ids):
    """PATCH inline: envia o creative spec completo direto no payload do ad."""
    all_vids = EXISTING_VIDS + [v for v in new_video_ids if v]
    log(f"FASE 2: PATCH inline nos 3 ads RMKT — adicionando {len(new_video_ids)} vídeos ({len(all_vids)} total)...")

    asset_feed = {
        "images": [{"hash": EXISTING_IMG}],
        "videos": [{"video_id": v} for v in all_vids],
        "bodies": [{"text": t} for t in COPY_RMKT["bodies"]],
        "titles": [{"text": t} for t in COPY_RMKT["titles"]],
        "call_to_action_types": ["SHOP_NOW"],
        "descriptions": [{"text": ""}],
        "link_urls": [{"website_url": TICKET_URL}],
        "ad_formats": ["AUTOMATIC_FORMAT"],
        "optimization_type": "REGULAR",
        "additional_data": {"multi_share_end_card": False, "is_click_to_message": False},
        "reasons_to_shop": False,
        "shops_bundle": False,
    }
    creative_spec = {
        "asset_feed_spec":   asset_feed,
        "object_story_spec": {"page_id": PAGE_ID},
        "use_dynamic_creative": False,
    }

    ok_count = 0
    for label, ad_id in ADS_RMKT.items():
        r, err = api_post(f"{_base()}/{ad_id}", {
            "creative": json.dumps(creative_spec),
        })
        if err:
            log(f"  {label} ad {ad_id} ERRO: {err}")
        else:
            log(f"  {label} ad {ad_id} PATCH OK ✓")
            ok_count += 1
    return ok_count

# ── 3. Upload imagem carrossel ────────────────────────────────────────────────

def upload_image(filepath):
    fpath = Path(filepath)
    stem  = fpath.stem
    name  = fpath.name
    ct    = "image/png" if name.lower().endswith(".png") else "image/jpeg"
    with open(fpath, "rb") as f:
        img_bytes = f.read()
    token    = _token()
    boundary = "----MetaBnd"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{stem}\"; filename=\"{name}\"\r\nContent-Type: {ct}\r\n\r\n"
    ).encode() + img_bytes + f"\r\n--{boundary}--\r\n".encode()
    url = f"{_base()}/{_acct()}/adimages?access_token={token}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
        for _, v in resp.get("images", {}).items():
            h = v.get("hash")
            log(f"    {name} → hash ...{h[-8:] if h else '?'} ✓")
            return h
        log(f"    ERRO imagem {name}: {resp}")
        return None
    except urllib.error.HTTPError as e:
        log(f"    ERRO {name}: {json.loads(e.read()).get('error',{}).get('message')}")
        return None

# ── 4. Creative carrossel ─────────────────────────────────────────────────────

def make_carousel_creative(label, capa_nome, resto_nomes, hash_map, body_text):
    ordered = [capa_nome] + resto_nomes
    cards = []
    for img_nome in ordered:
        h = hash_map.get(img_nome)
        if not h:
            log(f"    SKIP card {img_nome} (sem hash)")
            continue
        cards.append({
            "link":        TICKET_URL,
            "image_hash":  h,
            "name":        CARD_TITLES.get(img_nome, img_nome.replace(".png","")),
            "description": "Garanta seu ingresso — Individual R$90 | Família R$135",
            "call_to_action": {"type": "SHOP_NOW", "value": {"link": TICKET_URL}},
        })

    story_spec = {
        "page_id": PAGE_ID,
        "link_data": {
            "message": body_text,
            "link": TICKET_URL,
            "call_to_action": {"type": "SHOP_NOW"},
            "child_attachments": cards,
            "multi_share_end_card": False,
        },
    }
    cr_name = f"[RMKT] Carrossel Atrações {label} — 3ª Etapa SPID Cup 2026"
    r, err = api_post(f"{_base()}/{_acct()}/adcreatives", {
        "name":               cr_name,
        "object_story_spec":  json.dumps(story_spec),
        "use_dynamic_creative": "false",
    })
    if err:
        log(f"  ERRO creative {label}: {err}")
        return None
    cid = r.get("id")
    log(f"  creative carrossel {label} OK id={cid}")
    return cid

# ── 5. Criar ad PAUSED ────────────────────────────────────────────────────────

def create_ad(label_adset, label_criativo, creative_id):
    adset_id = ADSETS[label_adset]
    ad_name  = f"[RMKT] Carrossel Atrações {label_criativo} | {label_adset}"
    r, err = api_post(f"{_base()}/{_acct()}/ads", {
        "name":      ad_name,
        "adset_id":  adset_id,
        "creative":  json.dumps({"creative_id": creative_id}),
        "status":    "PAUSED",
        "tracking_specs": json.dumps([{
            "action.type": ["offsite_conversion"],
            "fb_pixel": [PIXEL_ID],
        }]),
    })
    ok = bool(r and r.get("id"))
    log(f"  ad {label_criativo} → {label_adset}: {'PAUSED ✓ id=' + r['id'] if ok else 'ERRO: ' + str(err)}")
    return r.get("id") if ok else None

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_env()
    log("=== Upload Carrossel + Vídeos — 3ª Etapa SPID Cup 2026 ===\n")

    # ── Fase 1: Upload vídeos ────────────────────────────────────────────────
    log("FASE 1: Upload vídeos novos")
    new_video_ids = []
    for fname, title in NOVOS_VIDEOS:
        vpath = ASSETS_DIR / fname
        if not vpath.exists():
            log(f"  SKIP {fname} — não encontrado")
            continue
        vid_id = upload_video(str(vpath), title)
        if vid_id:
            new_video_ids.append(vid_id)

    log(f"\n  {len(new_video_ids)}/{len(NOVOS_VIDEOS)} vídeos subidos\n")

    # ── Fase 2: PATCH inline nos ads RMKT ────────────────────────────────────
    if new_video_ids:
        ads_ok = patch_ads_add_videos(new_video_ids)
        log(f"  {ads_ok}/3 ads RMKT atualizados com novos vídeos")
    else:
        log("FASE 2: SKIP — nenhum vídeo novo subiu")
        ads_ok = 0
    print()

    # ── Fase 3: Upload imagens carrossel ─────────────────────────────────────
    log("FASE 3: Upload 11 imagens carrossel")
    all_images = sorted(CAROUSEL_DIR.glob("*.png"))
    hash_map = {}
    for img_path in all_images:
        h = upload_image(str(img_path))
        if h:
            hash_map[img_path.name] = h
    log(f"\n  {len(hash_map)}/11 imagens subidas\n")

    if len(hash_map) < 3:
        log("ERRO: menos de 3 imagens — abortando carrosseis")
        return

    # ── Fase 4 & 5: Creatives + Ads carrossel ────────────────────────────────
    log("FASE 4-5: Criando creatives e ads carrossel")
    COPY_BODIES = COPY_RMKT["bodies"]
    resultados = []
    for i, (label, capa, resto) in enumerate(VARIACOES):
        body_text = COPY_BODIES[i % len(COPY_BODIES)]
        adset_lbl = VARIACOES_ADSET[label]
        log(f"\n  [{label}] capa={capa} → adset {adset_lbl}")
        cr_id = make_carousel_creative(label, capa, resto, hash_map, body_text)
        if cr_id:
            ad_id = create_ad(adset_lbl, label, cr_id)
            resultados.append((label, adset_lbl, cr_id, ad_id))

    # ── Resumo ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    log("=== CONCLUÍDO ===")
    print(f"""
RESUMO:
  Vídeos subidos:   {len(new_video_ids)}/2 ({", ".join(new_video_ids) if new_video_ids else "nenhum"})
  Creative RMKT:    {ads_ok}/3 ads PATCHED inline com {len(EXISTING_VIDS)+len(new_video_ids)} vídeos total
  Imagens carrossel: {len(hash_map)}/11 subidas
  Carrosseis criados: {len(resultados)}/3""")
    for label, adset, cr_id, ad_id in resultados:
        status = "PAUSED ✓" if ad_id else "FALHOU"
        print(f"    {label} → {adset}: creative={cr_id} | ad={ad_id} | {status}")
    print("""
PRÓXIMO PASSO: Renato ativa os ads carrossel no Gerenciador de Anúncios.
""")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
