"""
Substitui V05 no Meta com a versao sem narrador.
Fluxo:
  1. Re-upload imagens (Meta retorna o mesmo hash se o arquivo nao mudou)
  2. Upload V05 v2 -> novo video_id
  3. Cria 2 novos creatives (PROSP + RMKT) com o video correto
  4. PATCH nos 6 ads existentes para usar os novos creatives
"""
import os, json, time, urllib.request, urllib.parse
from pathlib import Path

ASSETS_DIR = Path(r"E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3\variacoes-adforge-30jul")
TICKET_URL = "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"
PAGE_ID    = "102560719007016"

# Video IDs ja confirmados — so V05 muda
KNOWN_VIDEO_IDS = {
    "V01-familia-R120-zoomout.mp4": "1060581596619697",
    "V06-sexta-R40-pan.mp4":        "1516974276299351",
}

# IDs dos ads existentes (atualizados na sessao anterior)
ADS = {
    "A-01": "120249615428177680761" if False else None,  # filled below
}

# Adsets para buscar os ads
ADSETS_PROSP = {
    "A-01": "120249615428170761",
    "A-02": "120249601937260761",
}
ADSETS_RMKT = {
    "B-00": "120249615946860761",
    "B-01": "120249601941100761",
    "B-02": "120249615953090761",
    "B-03": "120249615972980761",
}

COPY_PROSP = {
    "bodies": [
        "Lote 1 do Individual esgotou. Lote 2 abriu por R$80 — arquibancada + box, arrancada real de 201m, carros a 300km/h. 28 a 30/Ago, Itatiba/SP.",
        "Traga a familia. R$120 garante 2 entradas na arquibancada + box. So online, 100 unidades. 3a Etapa SPID Cup, 28/Ago, Itatiba.",
        "Sexta e R$40. Sabado ou domingo e R$80. Passaporte (3 dias) R$120. Sao Paulo International Dragway, 28 a 30/Ago.",
        "O Individual virou de lote. R$70 acabou, agora e R$80. Ainda da tempo de garantir antes do proximo aumento. SPID Cup 3a Etapa, 28/Ago.",
        "201m de pista, Pro Mod a 355km/h, mais de 100 categorias em 3 dias. Individual 2o Lote R$80, Familia R$120. Garanta em agendaesportiva.com.br.",
    ],
    "titles": [
        "3a Etapa SPID Cup 2026",
        "Individual 2o Lote - R$80",
        "Familia - R$120 para 2 pessoas",
        "28-30/Ago - Itatiba/SP",
        "Lote 1 esgotou - 2o Lote aberto",
    ],
}
COPY_RMKT = {
    "bodies": [
        "Voce viu o SPID. Agosto chegou - Individual Lote 1 esgotou, 2o Lote no ar por R$80. 3a Etapa, 28/Ago, Itatiba/SP.",
        "R$70 acabou. Quem ainda nao comprou, o 2o Lote do Individual esta por R$80. Arquibancada + box. SPID Cup, 28 a 30/Ago.",
        "Familia no SPID Cup: 2 pessoas por R$120 na arquibancada + box. Obrigatorio documento de identificacao na retirada. 100 unidades, so online.",
        "A pista de 201m, o Pro Mod a 355km/h, a galera no box. 3a Etapa, 28/Ago, Sao Paulo International Dragway. Individual R$80.",
        "Voce ja esteve. Sabe o que esperar. 2o Lote do Individual por R$80 - vem.",
    ],
    "titles": [
        "Volta pra pista - 3a Etapa SPID Cup",
        "2o Lote disponivel - R$80",
        "28-30/Ago | Itatiba/SP",
        "Individual R$80 | Familia R$120",
        "3a Etapa - Garanta agora",
    ],
}

def load_env():
    for line in (Path.home() / ".adforge/.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

def api_post(url, data):
    token = os.environ["META_ACCESS_TOKEN"]
    data["access_token"] = token
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        return None, err.get("error", {})

def api_get(url):
    token = os.environ["META_ACCESS_TOKEN"]
    sep = "&" if "?" in url else "?"
    with urllib.request.urlopen(url + sep + "access_token=" + token, timeout=30) as r:
        return json.loads(r.read())

def upload_image(filepath, base, acct):
    name = Path(filepath).name
    stem = Path(filepath).stem
    print(f"  Imagem: {name}", end=" ... ", flush=True)
    with open(filepath, "rb") as f:
        img_bytes = f.read()
    token = os.environ["META_ACCESS_TOKEN"]
    boundary = "----MetaBoundary9F3A"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{stem}"; filename="{name}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + img_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{base}/act_{acct}/adimages?access_token={token}",
        data=body, method="POST",
    )
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
        for k, v in resp.get("images", {}).items():
            h = v.get("hash")
            print(f"OK (...{h[-8:] if h else '?'})")
            return h
        print(f"ERRO: {resp}")
        return None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f"ERRO: {err.get('error', {}).get('message', str(err))}")
        return None

def upload_video(filepath, base, acct):
    name = Path(filepath).name
    file_size = Path(filepath).stat().st_size
    print(f"  Video: {name}", end=" ... ", flush=True)
    r, err = api_post(f"{base}/act_{acct}/advideos", {
        "upload_phase": "start", "file_size": file_size,
    })
    if err:
        print(f"ERRO start: {err.get('message')}")
        return None
    upload_session_id = r["upload_session_id"]
    video_id = r["video_id"]
    with open(filepath, "rb") as f:
        video_bytes = f.read()
    token = os.environ["META_ACCESS_TOKEN"]
    boundary = "----VideoBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="upload_phase"\r\n\r\ntransfer\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="upload_session_id"\r\n\r\n{upload_session_id}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="start_offset"\r\n\r\n0\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="video_file_chunk"; filename="{name}"\r\n'
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode() + video_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{base}/act_{acct}/advideos", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r2:
            json.loads(r2.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f"ERRO transfer: {err.get('error', {}).get('message')}")
        return None
    r3, err3 = api_post(f"{base}/act_{acct}/advideos", {
        "upload_phase": "finish", "upload_session_id": upload_session_id,
    })
    if err3:
        print(f"ERRO finish: {err3.get('message')}")
        return None
    print(f"OK (video_id: ...{video_id[-8:]})")
    return video_id

def make_creative(name, copy, img_hashes, video_list, base, acct):
    asset_feed = {
        "images": [{"hash": h} for h in img_hashes if h],
        "videos": video_list,
        "bodies": [{"text": t} for t in copy["bodies"]],
        "titles": [{"text": t} for t in copy["titles"]],
        "call_to_action_types": ["SHOP_NOW"],
        "link_urls": [{"website_url": TICKET_URL}],
        "ad_formats": ["AUTOMATIC_FORMAT"],
    }
    data = {
        "name": name,
        "object_story_spec": json.dumps({"page_id": PAGE_ID}),
        "asset_feed_spec": json.dumps(asset_feed),
    }
    return api_post(f"{base}/act_{acct}/adcreatives", data)

def get_ads_in_adset(adset_id, base):
    resp = api_get(f"{base}/{adset_id}/ads?fields=id,name,status")
    return resp.get("data", [])

def patch_ad_creative(ad_id, creative_id, base):
    r, err = api_post(f"{base}/{ad_id}", {
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED",
    })
    return r, err

def main():
    load_env()
    VER  = os.environ.get("META_API_VERSION", "v25.0")
    BASE = f"https://graph.facebook.com/{VER}"
    ACCT = os.environ["META_AD_ACCOUNT_ID"].replace("act_", "")

    print("=== Fix V05 — Creative com som de arrancada ===\n")

    # 1. Imagens
    print("1. IMAGENS (re-upload — Meta retorna mesmo hash)")
    img_files = [
        "01-FAMILIA-2LOTE-R120-CORRIGIDA.png",
        "02-FAMILIA-R60-POR-PESSOA.png",
        "03-FAMILIA-DEADLINE-15AGO.png",
        "05-INDIVIDUAL-2LOTE-R80.png",
        "06-SEXTA-MEIO-INGRESSO-R40.png",
    ]
    img_hashes = {}
    for fname in img_files:
        fp = ASSETS_DIR / fname
        if fp.exists():
            h = upload_image(str(fp), BASE, ACCT)
            if h:
                img_hashes[fname] = h

    # 2. Videos
    print("\n2. VIDEOS")
    vid_refs = []
    # V01 e V06 — IDs conhecidos, bom audio
    for fname, known_id in KNOWN_VIDEO_IDS.items():
        print(f"  {fname} -> reuso ...{known_id[-8:]}")
        vid_refs.append({"video_id": known_id})

    # V05 — novo upload
    v05_path = ASSETS_DIR / "videos" / "V05-individual-R80.mp4"
    v05_id = upload_video(str(v05_path), BASE, ACCT)
    if v05_id:
        vid_refs.append({"video_id": v05_id})

    # 3. Creatives novos
    all_hashes = list(img_hashes.values())
    print("\n3. CREATIVES")
    cr_p, err_p = make_creative(
        "creative-3etapa-prospecto-2lote-v2",
        COPY_PROSP, all_hashes, vid_refs, BASE, ACCT,
    )
    cr_prosp_id = cr_p["id"] if cr_p else None
    print(f"  Prospecto: {'OK - ' + cr_prosp_id if cr_prosp_id else 'ERRO: ' + str(err_p)}")

    cr_r, err_r = make_creative(
        "creative-3etapa-rmkt-2lote-v2",
        COPY_RMKT, all_hashes, vid_refs, BASE, ACCT,
    )
    cr_rmkt_id = cr_r["id"] if cr_r else None
    print(f"  RMKT:      {'OK - ' + cr_rmkt_id if cr_rmkt_id else 'ERRO: ' + str(err_r)}")

    # 4. Patch ads
    print("\n4. PATCH ADS")
    ok = 0
    total = 0
    for label, adset_id in ADSETS_PROSP.items():
        cr_id = cr_prosp_id
        if not cr_id:
            print(f"  {label}: SKIP (sem creative)")
            continue
        for ad in get_ads_in_adset(adset_id, BASE):
            total += 1
            print(f"  {label} [{ad['status']}] {ad['name'][:35]}", end=" ... ")
            r, err = patch_ad_creative(ad["id"], cr_id, BASE)
            if r:
                print("OK -> PAUSED")
                ok += 1
            else:
                print(f"ERRO: {err.get('message', err)}")

    for label, adset_id in ADSETS_RMKT.items():
        cr_id = cr_rmkt_id
        if not cr_id:
            print(f"  {label}: SKIP (sem creative)")
            continue
        for ad in get_ads_in_adset(adset_id, BASE):
            total += 1
            print(f"  {label} [{ad['status']}] {ad['name'][:35]}", end=" ... ")
            r, err = patch_ad_creative(ad["id"], cr_id, BASE)
            if r:
                print("OK -> PAUSED")
                ok += 1
            else:
                print(f"ERRO: {err.get('message', err)}")

    print(f"\n=== Concluido: {ok}/{total} ads atualizados com V05 corrigido ===")
    print("\nRevise e ative no Gerenciador de Anuncios.")

if __name__ == "__main__":
    main()
