"""
Corrige estrutura das campanhas [COPIA] 3a Etapa SPID Cup 2026.
  1. Arquiva A-02 duplicata vazia (criado 25/Jul)
  2. Cria A-01 LKL 1% Purchase novo
  3. Cria creatives AUTOMATIC_FORMAT com todos os assets da 3a Etapa
  4. Cria ads em A-01, A-02, B-01 (fallback: atualiza se DCO)
"""
import os, json, urllib.request, urllib.parse
from pathlib import Path

# ── Assets 3a Etapa ───────────────────────────────────────────────────────────
IMG_HASHES = [
    "1e8ae06799d916fedb50b44816183452",  # INGRESSO-1oLOTE
    "27096ece834282f1d3b9b1900fc9ba60",  # FAMILIA-1oLOTE
    "8d56a779f493f938bfef8a9743bbbe67",  # PULSEIRA EXCLUSIVA PAIS
    "3b7c4d8c4078533986ceb44a6401a1c2",  # pulseiras limitadas-estatico
    "d8b72040514fd8e8291bf1cb23bb9859",  # brinde-pulseiras limitadas
]
VIDEOS = [
    {"video_id": "1686072822645220", "thumbnail_hash": "1e8ae06799d916fedb50b44816183452"},
    {"video_id": "1664904367954353", "thumbnail_hash": "27096ece834282f1d3b9b1900fc9ba60"},
    {"video_id": "1684013509564312", "thumbnail_hash": "8d56a779f493f938bfef8a9743bbbe67"},
]
TICKET_URL = "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"
PAGE_ID    = "102560719007016"

COPY_PROSP = {
    "bodies": [
        "A 3a Etapa do SPID Cup chega em 28 de agosto em Itatiba/SP. Arrancada, velocidade, adrenalina — tudo no mesmo fim de semana. Garanta seu ingresso do 1o Lote agora.",
        "28 a 30 de agosto, Itatiba/SP. Pista de 201m, carros ultrapassando 300km/h. Ingresso 1o Lote disponivel.",
        "Traga a familia! Pacote especial disponivel para o SPID Cup 2026. 28 a 30/Ago, Itatiba/SP.",
    ],
    "titles": [
        "3a Etapa SPID Cup 2026",
        "28-30/Ago — Itatiba/SP",
        "Ingresso 1o Lote Disponivel",
    ],
}
COPY_RMKT = {
    "bodies": [
        "Voce ja conhece o SPID Cup. Agosto chegou — a 3a Etapa vai ser ainda maior. Nao deixa passar.",
        "Ultima chance de garantir ingresso antes que o lote acabe. 28 a 30/Ago, Itatiba/SP.",
    ],
    "titles": [
        "Volta pra pista — 3a Etapa SPID Cup",
        "28-30/Ago | Seu ingresso te espera",
        "3a Etapa — Garanta agora",
    ],
}

# IDs fixos
PROSP_CAMP       = "120249601369080761"
A02_DUP_EMPTY    = "120249614341390761"   # duplicata vazia -> arquivar
A02_ID           = "120249601937260761"   # manter
B01_ID           = "120249601941100761"

# Targeting do A-01 original
A01_TARGETING = {
    "age_max": 65, "age_min": 18,
    "excluded_custom_audiences": [
        {"id": "23852023749220760"},
        {"id": "23852023752760760"},
        {"id": "120209063374030761"},
        {"id": "120210793604670761"},
        {"id": "120212486259070761"},
    ],
    "custom_audiences": [{"id": "120243828865620761"}],
    "geo_locations": {"countries": ["BR"], "location_types": ["home", "recent"]},
    "targeting_relaxation_types": {"lookalike": 0, "custom_audience": 0},
}


def load_env():
    for line in (Path.home() / ".adforge/.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))


def api_call(url, data, method="POST"):
    token = os.environ["META_ACCESS_TOKEN"]
    data["access_token"] = token
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        return None, err.get("error", {})


def api_get(url):
    token = os.environ["META_ACCESS_TOKEN"]
    full = f"{url}&access_token={token}" if "?" in url else f"{url}?access_token={token}"
    req = urllib.request.Request(full)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def make_creative(name, copy, base, acct):
    asset_feed = {
        "images": [{"hash": h} for h in IMG_HASHES],
        "videos": VIDEOS,
        "bodies": [{"text": t} for t in copy["bodies"]],
        "titles": [{"text": t} for t in copy["titles"]],
        "call_to_action_types": ["SHOP_NOW"],
        "link_urls": [{"website_url": TICKET_URL}],
        "ad_formats": ["AUTOMATIC_FORMAT"],
    }
    # Nota: object_story_spec deve ter APENAS page_id quando asset_feed_spec esta presente
    data = {
        "name": name,
        "object_story_spec": json.dumps({"page_id": PAGE_ID}),
        "asset_feed_spec": json.dumps(asset_feed),
    }
    return api_call(f"{base}/act_{acct}/adcreatives", data)


def create_or_update_ad(adset_id, creative_id, ad_name, base, acct):
    """Tenta criar ad; se DCO (erro 1885553), atualiza o existente."""
    r, err = api_call(f"{base}/act_{acct}/ads", {
        "name": ad_name,
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED",
    })
    if r:
        return "created", None

    sc = err.get("error_subcode") if err else None
    if sc == 1885553:
        # DCO: buscar ad existente e atualizar creative_id
        ads = api_get(f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}/{adset_id}/ads?fields=id,name")
        if ads.get("data"):
            ad_id = ads["data"][0]["id"]
            r2, err2 = api_call(f"https://graph.facebook.com/{os.environ.get('META_API_VERSION','v25.0')}/{ad_id}",
                                {"creative": json.dumps({"creative_id": creative_id})})
            if r2:
                return "updated_dco", None
            return None, err2
        return None, {"message": "DCO mas sem ad existente"}

    return None, err


def main():
    load_env()
    VER  = os.environ.get("META_API_VERSION", "v25.0")
    BASE = f"https://graph.facebook.com/{VER}"
    ACCT = os.environ["META_AD_ACCOUNT_ID"].replace("act_", "")

    # 1. Arquivar A-02 duplicata vazia
    print("1. Arquivando A-02 duplicata...")
    r, err = api_call(f"{BASE}/{A02_DUP_EMPTY}", {"status": "ARCHIVED"})
    print("   OK" if r else f"   ERRO: {err.get('message')}")

    # 2. Copiar A-01 do original (evita compliance_section ao criar do zero)
    ORIG_A01 = "120249458542640761"
    print("\n2. Copiando A-01 LKL 1% Purchase do original...")
    r2, err2 = api_call(f"{BASE}/{ORIG_A01}/copies", {
        "campaign_id": PROSP_CAMP,
        "status_option": "PAUSED",
        "deep_copy": "false",
    })
    if err2:
        print(f"   ERRO {err2.get('error_subcode')}: {err2.get('message')}")
        a01_new_id = None
    else:
        a01_new_id = r2.get("copied_adset_id") or (r2.get("copies") or [{}])[0].get("id")
        print(f"   OK — A-01 copiado")

    # 3. Criar creatives AUTOMATIC_FORMAT
    print("\n3. Criando creative Prospecto (AUTOMATIC_FORMAT)...")
    cr_p, err_cp = make_creative("creative-3etapa-prospecto-auto", COPY_PROSP, BASE, ACCT)
    cr_prosp_id = cr_p["id"] if cr_p else None
    print(f"   {'OK' if cr_prosp_id else 'ERRO: ' + str(err_cp.get('message') if err_cp else err_cp)}")

    print("\n4. Criando creative RMKT (AUTOMATIC_FORMAT)...")
    cr_r, err_cr = make_creative("creative-3etapa-rmkt-auto", COPY_RMKT, BASE, ACCT)
    cr_rmkt_id = cr_r["id"] if cr_r else None
    print(f"   {'OK' if cr_rmkt_id else 'ERRO: ' + str(err_cr.get('message') if err_cr else err_cr)}")

    # 4. Ads
    tasks = []
    if a01_new_id and cr_prosp_id:
        tasks.append((a01_new_id, cr_prosp_id, "[PROSP] 3aEtapa A-01 LKL | auto", "A-01"))
    if cr_prosp_id:
        tasks.append((A02_ID, cr_prosp_id, "[PROSP] 3aEtapa A-02 Eng | auto", "A-02"))
    if cr_rmkt_id:
        tasks.append((B01_ID, cr_rmkt_id, "[RMKT] 3aEtapa B-01 VV | auto", "B-01"))

    for adset_id, creative_id, ad_name, label in tasks:
        print(f"\n5. Subindo ad em {label}...")
        action, err = create_or_update_ad(adset_id, creative_id, ad_name, BASE, ACCT)
        if action:
            print(f"   OK ({action})")
        else:
            sc = err.get("error_subcode") if err else "?"
            print(f"   ERRO {sc}: {err.get('message') if err else err}")

    print("\n=== Concluido ===")


if __name__ == "__main__":
    main()
