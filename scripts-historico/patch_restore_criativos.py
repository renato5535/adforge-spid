"""
Restaura criativos nos ads B-00, B-01, B-02 da RMKT 3ª Etapa.
Remove referências à família (encerrado hoje 28/Ago às 18h).
Adiciona: 6 vídeos + COMPRA-SITE (3 vars) + SORTEIO-DRAGSTER + INGRESSO-BILHETERIA.
Copies atualizadas para evento ao vivo (começa hoje).
"""
import sys, json, urllib.parse, urllib.request
sys.path.insert(0, __import__('os').path.expanduser('~/.adforge/daily_analyst'))
from common import load_env

env = load_env()
token   = env.get('META_ACCESS_TOKEN', '')
api_ver = env.get('META_API_VERSION', 'v25.0')
BASE    = 'https://graph.facebook.com/%s' % api_ver

# --- Ads a PATCHar (B-00, B-01, B-02 — RMKT 3ª Etapa) ---
ADS = {
    'B-00 Pageview 180D':        '120249615979300761',
    'B-01 Video View 95% 180D':  '120249601960410761',
    'B-02 Purchase 180D':        '120249615981500761',
}

# --- Asset feed spec ---
ASSET_FEED = {
    "videos": [
        {"video_id": "1751357062657146"},  # v01-corr Sprint Final
        {"video_id": "2130921221187540"},  # v02 Sprint Final
        {"video_id": "910059035503249"},   # v03 Sprint Final
        {"video_id": "4513429778925528"},  # v04 Sprint Final
        {"video_id": "2154051288509185"},  # v04-novo Sprint Final
        {"video_id": "1786638312585666"},  # v05 Sprint Final
    ],
    "images": [
        {"hash": "82e8c374d5e4733f54fede56eecfc819"},   # COMPRA-SITE.png
        {"hash": "7fba41bd032187f669c28168105febb4"},   # COMPRA-SITE-var-01.png
        {"hash": "5c56959f34cbcd358b9a5b330800a344"},   # COMPRA-SITE-var-02.png
        {"hash": "dca3de87331093fb17803cb061ab8b07"},   # SORTEIO-DRAGSTER.png
        # total: 4 imagens + 6 vídeos = 10 (limite Meta)
    ],
    "bodies": [
        {"text": "Começa hoje. 3ª Etapa SPID Cup — 28 a 30/Ago no SPID, Itatiba/SP.\n\nIndividual R$90. Bilheteria presencial aberta nos 3 dias. Só precisa do documento — nada pra imprimir."},
        {"text": "201m de pista. Pro Mod a 355km/h. Hoje ao vivo.\n\nSó existe ao vivo — Individual R$90. São Paulo International Dragway, Itatiba."},
        {"text": "Você viu o SPID. Agora é ao vivo.\n\n3ª Etapa começa hoje — bilheteria no local. Individual R$90. SPID, Itatiba/SP."},
        {"text": "Volta pra pista. 3ª Etapa SPID Cup começa hoje — Itatiba.\n\nIndividual R$90. Bilheteria aberta. Não existe câmera lenta ao vivo."},
        {"text": "A arrancada começou. Pro Mods a 355km/h, 201m de pista.\n\nBilheteria aberta nos 3 dias. Individual R$90 — chega, paga e entra."},
    ],
    "titles": [
        {"text": "28–30/Ago | Itatiba/SP"},
        {"text": "3ª Etapa SPID Cup — começa hoje"},
        {"text": "Individual R$90 | Bilheteria aberta"},
        {"text": "Bilheteria presencial — 3 dias"},
        {"text": "São Paulo International Dragway"},
    ],
    "descriptions": [
        {"text": "Bilheteria presencial aberta nos 3 dias — SPID, Itatiba/SP"}
    ],
    "call_to_action_types": ["SHOP_NOW"],
    "link_urls": [
        {"website_url": "https://agendaesportiva.com.br/#!/evento/3-etapa-spid-cup-2026"}
    ],
    "ad_formats": ["AUTOMATIC_FORMAT"],
    "optimization_type": "REGULAR",
    "additional_data": {
        "multi_share_end_card": False,
        "is_click_to_message": False,
    },
    "reasons_to_shop": False,
    "shops_bundle": False,
}

CREATIVE_SPEC = {
    "asset_feed_spec": ASSET_FEED,
    "object_story_spec": {"page_id": "102560719007016"},
}

def patch_ad(ad_id, ad_name):
    url = '%s/%s' % (BASE, ad_id)
    payload = urllib.parse.urlencode({
        'creative': json.dumps(CREATIVE_SPEC),
        'access_token': token,
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload,
                                  headers={'User-Agent': 'adforge/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode('utf-8'))
            return resp, None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode('utf-8'))
        except Exception:
            body = {'error': {'message': str(e)}}
        return body, 'HTTP %s' % e.code
    except Exception as e:
        return None, str(e)

print('\n=== PATCH — Restaurando criativos (6 vídeos + COMPRA-SITE ×3 + SORTEIO-DRAGSTER + BILHETERIA) ===\n')

for nome, ad_id in ADS.items():
    resp, err = patch_ad(ad_id, nome)
    if err:
        print('FALHA [%s] %s: %s — %s' % (ad_id, nome, err, json.dumps(resp or {})))
    else:
        success = resp.get('success', False)
        if success:
            print('OK    [%s] %s' % (ad_id, nome))
        else:
            print('ERR   [%s] %s: %s' % (ad_id, nome, json.dumps(resp)))

print('\nPronto. Verifique status no Gerenciador de Anúncios.')
