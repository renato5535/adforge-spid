"""
Sobe V05 corrigido (audio real de arrancada) e atualiza creatives nos 6 ads.
NAO altera o status dos ads — mantem ACTIVE quem ja esta ACTIVE.
Aprovado pelo Renato em 31/Jul.
"""
import os, json, urllib.request, urllib.parse
from pathlib import Path

ASSETS_DIR = Path(r"E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3\variacoes-adforge-30jul")
TICKET_URL = "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"
PAGE_ID    = "102560719007016"

KNOWN_VIDEO_IDS = {
    "V01-familia-R120-zoomout.mp4": "1060581596619697",
    "V06-sexta-R40-pan.mp4":        "1516974276299351",
}

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
    print(f"  {name}", end=" ... ", flush=True)
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
    print(f"  {name} ({file_size//1024}KB)", end=" ... ", flush=True)
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
        with urllib.request.urlopen(req, timeout=180) as r2:
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
    print(f"OK (id: ...{video_id[-8:]})")
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

def patch_ad_creative_only(ad_id, creative_id, base):
    # Apenas troca o creative — sem alterar status
    return api_post(f"{base}/{ad_id}", {
        "creative": json.dumps({"creative_id": creative_id}),
    })

def main():
    load_env()
    VER  = os.environ.get("META_API_VERSION", "v25.0")
    BASE = f"https://graph.facebook.com/{VER}"
    ACCT = os.environ["META_AD_ACCOUNT_ID"].replace("act_", "")

    print("=== Upload V05 corrigido + novos creatives (sem pausar ads) ===\n")

    # 1. Imagens
    print("1. IMAGENS")
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
    for fname, vid_id in KNOWN_VIDEO_IDS.items():
        print(f"  {fname} -> reuso ...{vid_id[-8:]}")
        vid_refs.append({"video_id": vid_id})

    v05_path = ASSETS_DIR / "videos" / "V05-individual-R80-fixaudio.mp4"
    v05_id = upload_video(str(v05_path), BASE, ACCT)
    if v05_id:
        vid_refs.append({"video_id": v05_id})

    # 3. Creatives
    all_hashes = list(img_hashes.values())
    print("\n3. CREATIVES")
    cr_p, err_p = make_creative(
        "creative-3etapa-prospecto-2lote-v3",
        COPY_PROSP, all_hashes, vid_refs, BASE, ACCT,
    )
    cr_prosp_id = cr_p["id"] if cr_p else None
    print(f"  Prospecto: {'OK' if cr_prosp_id else 'ERRO: ' + str(err_p)}")

    cr_r, err_r = make_creative(
        "creative-3etapa-rmkt-2lote-v3",
        COPY_RMKT, all_hashes, vid_refs, BASE, ACCT,
    )
    cr_rmkt_id = cr_r["id"] if cr_r else None
    print(f"  RMKT:      {'OK' if cr_rmkt_id else 'ERRO: ' + str(err_r)}")

    # 4. Patch ads — SEM alterar status
    print("\n4. PATCH ADS (mantem status atual)")
    ok = 0
    total = 0
    for label, adset_id in ADSETS_PROSP.items():
        if not cr_prosp_id:
            continue
        for ad in get_ads_in_adset(adset_id, BASE):
            total += 1
            print(f"  {label} [{ad['status']}] {ad['name'][:35]}", end=" ... ")
            r, err = patch_ad_creative_only(ad["id"], cr_prosp_id, BASE)
            if r:
                print(f"OK (mantido {ad['status']})")
                ok += 1
            else:
                print(f"ERRO: {err.get('message', err)}")

    for label, adset_id in ADSETS_RMKT.items():
        if not cr_rmkt_id:
            continue
        for ad in get_ads_in_adset(adset_id, BASE):
            total += 1
            print(f"  {label} [{ad['status']}] {ad['name'][:35]}", end=" ... ")
            r, err = patch_ad_creative_only(ad["id"], cr_rmkt_id, BASE)
            if r:
                print(f"OK (mantido {ad['status']})")
                ok += 1
            else:
                print(f"ERRO: {err.get('message', err)}")

    print(f"\n=== {ok}/{total} ads atualizados com V05 corrigido ===")

if __name__ == "__main__":
    main()
