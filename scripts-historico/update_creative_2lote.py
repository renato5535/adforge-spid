"""
Atualiza o creative dos ads existentes (Lote 1 -> Lote 2) e pausa para revisao.
DCO adsets aceitam max 1 ad por conjunto, entao nao e possivel criar novos.
Solucao: PATCH no ad existente com o novo creative_id + status=PAUSED.
"""
import os, json, urllib.request, urllib.parse
from pathlib import Path

# Creatives criados pela sessao anterior
CR_PROSP = "1770417230633162"
CR_RMKT  = "1054947423656339"

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

def load_env():
    for line in (Path.home() / ".adforge/.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

def api_get(url):
    token = os.environ["META_ACCESS_TOKEN"]
    sep = "&" if "?" in url else "?"
    with urllib.request.urlopen(url + sep + "access_token=" + token, timeout=30) as r:
        return json.loads(r.read())

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

def get_ads_in_adset(adset_id, base):
    url = f"{base}/{adset_id}/ads?fields=id,name,status"
    resp = api_get(url)
    return resp.get("data", [])

def update_ad(ad_id, creative_id, base):
    url = f"{base}/{ad_id}"
    r, err = api_post(url, {
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED",
    })
    return r, err

def main():
    load_env()
    VER  = os.environ.get("META_API_VERSION", "v25.0")
    BASE = f"https://graph.facebook.com/{VER}"

    print("=== Atualiza Creative 2o Lote nos Adsets Existentes ===\n")
    print(f"  Creative Prospecto: {CR_PROSP}")
    print(f"  Creative RMKT:      {CR_RMKT}\n")

    results = []

    print("--- ADSETS PROSPECTO ---")
    for label, adset_id in ADSETS_PROSP.items():
        ads = get_ads_in_adset(adset_id, BASE)
        if not ads:
            print(f"  {label}: nenhum ad encontrado — pulando")
            continue
        for ad in ads:
            ad_id = ad["id"]
            ad_name = ad["name"]
            old_status = ad["status"]
            print(f"  {label} [{old_status}] {ad_name[:40]}", end=" ... ")
            r, err = update_ad(ad_id, CR_PROSP, BASE)
            if r:
                print(f"OK -> PAUSED (id: ...{ad_id[-8:]})")
                results.append((label, "PROSP", True, ad_id))
            else:
                print(f"ERRO: {err.get('message', err)}")
                results.append((label, "PROSP", False, ad_id))

    print("\n--- ADSETS RMKT ---")
    for label, adset_id in ADSETS_RMKT.items():
        ads = get_ads_in_adset(adset_id, BASE)
        if not ads:
            print(f"  {label}: nenhum ad encontrado — pulando")
            continue
        for ad in ads:
            ad_id = ad["id"]
            ad_name = ad["name"]
            old_status = ad["status"]
            print(f"  {label} [{old_status}] {ad_name[:40]}", end=" ... ")
            r, err = update_ad(ad_id, CR_RMKT, BASE)
            if r:
                print(f"OK -> PAUSED (id: ...{ad_id[-8:]})")
                results.append((label, "RMKT", True, ad_id))
            else:
                print(f"ERRO: {err.get('message', err)}")
                results.append((label, "RMKT", False, ad_id))

    ok = sum(1 for _, _, s, _ in results if s)
    print(f"\n=== Concluido: {ok}/{len(results)} ads atualizados e PAUSADOS ===")
    print("\nProximos passos:")
    print("  1. Revise os criativos no Gerenciador de Anuncios")
    print("  2. Ative os adsets que quiser rodar com Lote 2")
    print("  3. Recarregue saldo Meta (esgota ~09/Ago com R$1.459)")

if __name__ == "__main__":
    main()
