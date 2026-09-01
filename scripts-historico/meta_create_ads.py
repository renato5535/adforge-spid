"""
Cria ads em todos os adsets da 3a Etapa SPID Cup com Advantage+ Creative DESATIVADO.

Uso:
  python meta_create_ads.py --video-id <VIDEO_ID> --copy-index <0|1|2>
  python meta_create_ads.py --video-id <VIDEO_ID>          # usa copy 0 (padrao)

Copy indexes:
  0 = Ingresso 1o Lote (prospecto)
  1 = Remarketing engajados
  2 = Familia / pacote

PADRAO DE UPLOAD: standard_enhancements OPT_OUT (sem IA de criativos da Meta).
"""
import os, sys, json, urllib.request, urllib.parse, argparse
from pathlib import Path

# ── Configuracoes da campanha 3a Etapa ─────────────────────────────────────────
PAGE_ID = "102560719007016"  # SPID CUP

TICKET_URL = "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"

# Adsets: (id, nome, campanha)
ADSETS = [
    ("120249458523540761", "B-00 Pageview 180D",          "RMKT"),
    ("120249458539200761", "B-01 Video View 95% 180D",    "RMKT"),
    ("120249458540310761", "B-02 Purchase 180D",           "RMKT"),
    ("120249458541220761", "B-03 InitiateCheckout 180D",   "RMKT"),
    ("120249458542640761", "A-01 LKL 1% Purchase 180D",   "PROSPECTO"),
    ("120249458543460761", "A-02 Engajamento 365D",        "PROSPECTO"),
]

# Copies por index
COPIES = [
    # 0 — Ingresso / prospecto
    {
        "primary_text": "A 3a Etapa do SPID Cup chega em 28 de agosto em Itatiba/SP. Arrancada, velocidade, adrenalina — tudo no mesmo fim de semana. Garanta seu ingresso do 1o Lote agora.",
        "headline": "3a Etapa SPID Cup — Ingresso 1o Lote",
        "description": "28 a 30 de agosto | Itatiba/SP | Garanta ja",
        "cta": "BUY_TICKETS",
    },
    # 1 — Remarketing
    {
        "primary_text": "Voce ja conhece o SPID Cup. Agosto chegou — a 3a Etapa vai ser ainda maior. Nao deixa passar.",
        "headline": "Volta pra pista — 3a Etapa SPID Cup",
        "description": "28 a 30 de agosto | Itatiba/SP",
        "cta": "BUY_TICKETS",
    },
    # 2 — Familia
    {
        "primary_text": "Traga a familia para o maior festival de arrancada do Brasil. Pacote Familia com desconto — 1 ingresso Adulto + 1 Kids incluso. 28 a 30 de agosto, Itatiba/SP.",
        "headline": "Pacote Familia — 3a Etapa SPID Cup",
        "description": "Adulto + Kids | 28 a 30/ago | Itatiba/SP",
        "cta": "BUY_TICKETS",
    },
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_env():
    env = Path.home() / ".adforge" / ".env"
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip('"').strip("'"))

def api_post(url, data: dict, token: str):
    data["access_token"] = token
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        return None, err.get("error", {})

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True, help="ID do video Meta (de meta_upload_video.py)")
    parser.add_argument("--copy-index", type=int, default=0, choices=[0, 1, 2], help="Index do copy (0=ingresso, 1=rmkt, 2=familia)")
    parser.add_argument("--thumbnail-hash", default="", help="Hash da imagem de thumbnail (obrigatorio na v25+)")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o payload sem criar")
    args = parser.parse_args()

    load_env()
    TOKEN   = os.environ["META_ACCESS_TOKEN"]
    API_VER = os.environ.get("META_API_VERSION", "v25.0")
    BASE    = f"https://graph.facebook.com/{API_VER}"

    copy = COPIES[args.copy_index]
    print(f"Copy {args.copy_index}: {copy['headline']}")
    print(f"Video ID: {args.video_id}")
    print()

    for adset_id, adset_name, camp_type in ADSETS:
        ad_name = f"[{camp_type}] {copy['headline'][:40]} | vid-{args.video_id[-6:]}"

        # 1. Criar creative com OPT_OUT
        if not args.thumbnail_hash:
            print(f"  AVISO: --thumbnail-hash obrigatorio na v25+ para video ads. Adset {adset_name} sera pulado.")
            continue

        video_data = {
            "video_id": args.video_id,
            "image_hash": args.thumbnail_hash,
            "message": copy["primary_text"],
            "title": copy["headline"],
            "call_to_action": {
                "type": copy["cta"],
                "value": {"link": TICKET_URL},
            },
        }

        creative_body = {
            "name": f"creative-{args.video_id[-6:]}-{args.copy_index}",
            "object_story_spec": json.dumps({
                "page_id": PAGE_ID,
                "video_data": video_data,
            }),
        }

        if args.dry_run:
            print(f"[DRY-RUN] Adset {adset_name}:")
            print(json.dumps(creative_body, indent=2, ensure_ascii=False))
            print()
            continue

        # Criar creative
        result, err = api_post(
            f"{BASE}/act_{os.environ['META_AD_ACCOUNT_ID'].replace('act_','')}/adcreatives",
            creative_body,
            TOKEN,
        )
        if err:
            print(f"  ERR creative {adset_name}: {err.get('message')}")
            continue
        creative_id = result["id"]

        # 2. Criar ad no adset
        ad_body = {
            "name": ad_name,
            "adset_id": adset_id,
            "creative": json.dumps({"creative_id": creative_id}),
            "status": "ACTIVE",
        }
        result2, err2 = api_post(f"{BASE}/act_{os.environ['META_AD_ACCOUNT_ID'].replace('act_','')}/ads", ad_body, TOKEN)
        if err2:
            print(f"  ERR ad {adset_name}: {err2.get('message')}")
        else:
            print(f"  OK  {adset_name} -> Ad {result2['id']} | Creative {creative_id}")

    if not args.dry_run:
        print("\nAds criados com Advantage+ Creative DESATIVADO (OPT_OUT).")

if __name__ == "__main__":
    main()
