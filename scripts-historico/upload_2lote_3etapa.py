"""
Upload assets do 2º Lote — 3ª Etapa SPID Cup 2026
Fluxo: upload imagens/vídeos → criar creative DCO → criar ads PAUSED

Assets a subir:
  Imagens:
    01-FAMILIA-2LOTE-R120-CORRIGIDA.png
    02-FAMILIA-R60-POR-PESSOA.png
    03-FAMILIA-DEADLINE-15AGO.png        (gerado pelo Higgsfield)
    05-INDIVIDUAL-2LOTE-R80.png          (gerado pelo Higgsfield)
    06-SEXTA-MEIO-INGRESSO-R40.png
    04-INDIVIDUAL-ULTIMAS-VAGAS-R70.png  (ainda válido: 1 vaga restante)
  Vídeos:
    V01-familia-R120-zoomout.mp4
    V05-individual-R80.mp4               (animação do R$80)
    V06-sexta-R40-pan.mp4

Copy: 2º lote — atualizada para refletir Individual R$80, Família R$120
"""
import os, json, time, urllib.request, urllib.parse
from pathlib import Path

ASSETS_DIR = Path(r"E:\SPID-Motor Show\Spid Cup\Eventos-2026\Etapa 3\variacoes-adforge-30jul")
TICKET_URL = "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"
PAGE_ID    = "102560719007016"

# IDs dos adsets ativos da 3ª Etapa (confirmados via API 30/Jul)
CAMP_PROSP = "120249601369080761"   # [PROSPECTO][CONVERSÃO] 3ª Etapa SPID Cup 2026 [COPIA]
CAMP_RMKT  = "120249601416320761"   # [RMKT][CONVERSÃO] 3ª Etapa SPID Cup 2026 [COPIA]

ADSETS_PROSP = {
    "A-01": "120249615428170761",   # LKL 1% Purchase 180D — Cópia
    "A-02": "120249601937260761",   # Engajamento 365D — Cópia
}
ADSETS_RMKT = {
    "B-00": "120249615946860761",   # Pageview 180D
    "B-01": "120249601941100761",   # Video View 95% 180D — Cópia
    "B-02": "120249615953090761",   # Purchase 180D
    "B-03": "120249615972980761",   # InitiateCheckout 180D
}

# ── Copy 2º Lote ──────────────────────────────────────────────────────────────

COPY_PROSP = {
    "bodies": [
        "Lote 1 do Individual esgotou. Lote 2 abriu por R$80 — arquibancada + box, arrancada real de 201m, carros a 300km/h. 28 a 30/Ago, Itatiba/SP.",
        "Traga a família. R$120 garante 2 entradas na arquibancada + box. Só online, 100 unidades. 3ª Etapa SPID Cup, 28/Ago, Itatiba.",
        "Sexta é R$40. Sábado ou domingo é R$80. Passaporte (3 dias) R$120. São Paulo International Dragway, 28 a 30/Ago.",
        "O Individual virou de lote. R$70 acabou, agora é R$80. Ainda dá tempo de garantir antes do próximo aumento. SPID Cup 3ª Etapa, 28/Ago.",
        "201m de pista, Pro Mod a 355km/h, mais de 100 categorias em 3 dias. Individual 2º Lote R$80, Família R$120. Garanta em agendaesportiva.com.br.",
    ],
    "titles": [
        "3ª Etapa SPID Cup 2026",
        "Individual 2º Lote — R$80",
        "Família — R$120 para 2 pessoas",
        "28–30/Ago — Itatiba/SP",
        "Lote 1 esgotou — 2º Lote aberto",
    ],
}

COPY_RMKT = {
    "bodies": [
        "Você viu o SPID. Agosto chegou — Individual Lote 1 esgotou, 2º Lote no ar por R$80. 3ª Etapa, 28/Ago, Itatiba/SP.",
        "R$70 acabou. Quem ainda não comprou, o 2º Lote do Individual está por R$80. Arquibancada + box. SPID Cup, 28 a 30/Ago.",
        "Família no SPID Cup: 2 pessoas por R$120 na arquibancada + box. Obrigatório documento de identificação na retirada. 100 unidades, só online.",
        "A pista de 201m, o Pro Mod a 355km/h, a galera no box. 3ª Etapa, 28/Ago, São Paulo International Dragway. Individual R$80.",
        "Você já esteve. Sabe o que esperar. 2º Lote do Individual por R$80 — vem.",
    ],
    "titles": [
        "Volta pra pista — 3ª Etapa SPID Cup",
        "2º Lote disponível — R$80",
        "28–30/Ago | Itatiba/SP",
        "Individual R$80 | Família R$120",
        "3ª Etapa — Garanta agora",
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

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


# Video IDs já subidos na sessão anterior — reutilizar sem re-upload
KNOWN_VIDEO_IDS = {
    "V01-familia-R120-zoomout.mp4": "1060581596619697",
    "V05-individual-R80.mp4":       "1043103268302835",
    "V06-sexta-R40-pan.mp4":        "1516974276299351",
}

# ── Upload de imagem ──────────────────────────────────────────────────────────

def upload_image(filepath, base, acct):
    name = Path(filepath).name
    stem = Path(filepath).stem  # campo name deve ser o nome do arquivo (sem ext)
    print(f"  Upload imagem: {name}", end=" ... ", flush=True)
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
        data=body,
        method="POST",
    )
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
        images = resp.get("images", {})
        for k, v in images.items():
            h = v.get("hash")
            print(f"OK (hash: ...{h[-8:] if h else '?'})")
            return h
        print(f"ERRO: sem hash — {resp}")
        return None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f"ERRO: {err.get('error', {}).get('message', str(err))}")
        return None


# ── Upload de vídeo ───────────────────────────────────────────────────────────

def upload_video(filepath, base, acct):
    name = Path(filepath).name
    file_size = Path(filepath).stat().st_size
    print(f"  Upload vídeo: {name}", end=" ... ", flush=True)

    # 1. Iniciar sessão de upload
    r, err = api_post(f"{base}/act_{acct}/advideos", {
        "upload_phase": "start",
        "file_size": file_size,
    })
    if err:
        print(f"ERRO start: {err.get('message')}")
        return None
    upload_session_id = r.get("upload_session_id")
    video_id = r.get("video_id")

    # 2. Upload do arquivo
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

    # 3. Finalizar
    r3, err3 = api_post(f"{base}/act_{acct}/advideos", {
        "upload_phase": "finish",
        "upload_session_id": upload_session_id,
    })
    if err3:
        print(f"ERRO finish: {err3.get('message')}")
        return None

    print(f"OK (video_id: {video_id})")
    return video_id


# ── Creative DCO ──────────────────────────────────────────────────────────────

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


# ── Ad ────────────────────────────────────────────────────────────────────────

def create_ad(adset_id, creative_id, ad_name, base, acct):
    r, err = api_post(f"{base}/act_{acct}/ads", {
        "name": ad_name,
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED",
    })
    return r, err


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_env()
    VER  = os.environ.get("META_API_VERSION", "v25.0")
    BASE = f"https://graph.facebook.com/{VER}"
    ACCT = os.environ["META_AD_ACCOUNT_ID"].replace("act_", "")

    print("=== Upload 2º Lote — 3ª Etapa SPID Cup ===\n")

    # ── 1. Upload imagens ─────────────────────────────────────────────────────
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
        if not fp.exists():
            print(f"  SKIP (não encontrado): {fname}")
            continue
        h = upload_image(str(fp), BASE, ACCT)
        if h:
            img_hashes[fname] = h

    # ── 2. Vídeos — usa IDs já subidos, não re-envia ──────────────────────────
    print("\n2. VÍDEOS (aproveitando IDs da sessão anterior)")
    vid_files = [
        ("V01-familia-R120-zoomout.mp4",  img_hashes.get("01-FAMILIA-2LOTE-R120-CORRIGIDA.png")),
        ("V05-individual-R80.mp4",        img_hashes.get("05-INDIVIDUAL-2LOTE-R80.png")),
        ("V06-sexta-R40-pan.mp4",         img_hashes.get("06-SEXTA-MEIO-INGRESSO-R40.png")),
    ]
    vid_refs = []
    for fname, thumb_hash in vid_files:
        known_id = KNOWN_VIDEO_IDS.get(fname)
        if known_id:
            print(f"  {fname} -> reutilizando video_id: ...{known_id[-6:]}")
            entry = {"video_id": known_id}
            if thumb_hash:
                entry["thumbnail_hash"] = thumb_hash
            vid_refs.append(entry)
            continue
        fp = ASSETS_DIR / "videos" / fname
        if not fp.exists():
            print(f"  SKIP (não encontrado): {fname}")
            continue
        vid_id = upload_video(str(fp), BASE, ACCT)
        if vid_id:
            entry = {"video_id": vid_id}
            if thumb_hash:
                entry["thumbnail_hash"] = thumb_hash
            vid_refs.append(entry)

    # ── 3. Creatives ──────────────────────────────────────────────────────────
    all_hashes = list(img_hashes.values())
    print("\n3. CREATIVES")

    print("  Creative Prospecto 2º Lote...", end=" ")
    cr_p, err_p = make_creative(
        "creative-3etapa-prospecto-2lote",
        COPY_PROSP, all_hashes, vid_refs, BASE, ACCT,
    )
    cr_prosp_id = cr_p["id"] if cr_p else None
    print(f"{'OK' if cr_prosp_id else 'ERRO: ' + str(err_p)}")

    print("  Creative RMKT 2º Lote...", end=" ")
    cr_r, err_r = make_creative(
        "creative-3etapa-rmkt-2lote",
        COPY_RMKT, all_hashes, vid_refs, BASE, ACCT,
    )
    cr_rmkt_id = cr_r["id"] if cr_r else None
    print(f"{'OK' if cr_rmkt_id else 'ERRO: ' + str(err_r)}")

    # ── 4. Ads (PAUSED) ───────────────────────────────────────────────────────
    print("\n4. ADS (PAUSED — aguardam ativação manual)")
    ad_results = []

    if cr_prosp_id:
        for label, adset_id in ADSETS_PROSP.items():
            ad_name = f"[PROSP] 3aEtapa {label} 2Lote | auto"
            print(f"  {label} Prosp...", end=" ")
            r, err = create_ad(adset_id, cr_prosp_id, ad_name, BASE, ACCT)
            ok = bool(r and r.get("id"))
            print("OK" if ok else f"ERRO: {err}")
            ad_results.append((label, "PROSP", ok))

    if cr_rmkt_id:
        for label, adset_id in ADSETS_RMKT.items():
            ad_name = f"[RMKT] 3aEtapa {label} 2Lote | auto"
            print(f"  {label} RMKT...", end=" ")
            r, err = create_ad(adset_id, cr_rmkt_id, ad_name, BASE, ACCT)
            ok = bool(r and r.get("id"))
            print("OK" if ok else f"ERRO: {err}")
            ad_results.append((label, "RMKT", ok))

    ok_ads = sum(1 for _, _, ok in ad_results if ok)
    print(f"\n=== Concluído ===")
    print(f"\nResumo:")
    print(f"  Imagens subidas:  {len(img_hashes)}")
    print(f"  Vídeos subidos:   {len(vid_refs)}")
    print(f"  Creative Prosp:   {'OK — ' + cr_prosp_id if cr_prosp_id else 'FALHOU'}")
    print(f"  Creative RMKT:    {'OK — ' + cr_rmkt_id if cr_rmkt_id else 'FALHOU'}")
    print(f"  Ads criados:      {ok_ads}/{len(ad_results)} (todos PAUSED)")


if __name__ == "__main__":
    main()
