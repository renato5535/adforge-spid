"""
patch_ads_tracking.py
PATCH nos 5 ads com novo creative_id + tracking_specs atualizados
(resolve o erro 2446391 que ocorre por tracking_specs referenciarem post ID antigo).
"""
import sys, os, json, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'daily_analyst'))
from common import load_env

env     = load_env()
TOKEN   = env.get('META_ACCESS_TOKEN', '')
API_VER = env.get('META_API_VERSION', 'v25.0')
BASE    = 'https://graph.facebook.com/%s' % API_VER
PIXEL   = '2522706167879355'
PAGE_ID = '102560719007016'

# Mapeamento: ad_id -> novo creative_id (criados em patch_lote_final.py)
AD_TO_CREATIVE = {
    '120249615677680761': '1587136873199891',   # A-01 PROSP
    '120249601960410761': '3232913090247573',   # B-01 Volta
    '120249615979300761': '1796858211753941',   # B-00 Pageview
    '120249615985150761': '2163709578361062',   # B-03 InitiateCheckout
    '120249615981500761': '1846913479398605',   # B-02 Purchase
}


def get_post_id(creative_id):
    url = '%s/%s' % (BASE, creative_id)
    resp = requests.get(url, params={
        'fields': 'effective_object_story_id',
        'access_token': TOKEN,
    }, timeout=30)
    story_id = resp.json().get('effective_object_story_id', '')
    if '_' in story_id:
        return story_id.split('_')[1]
    return None


def build_tracking_specs(post_id):
    return [
        {
            'action.type': ['offsite_conversion'],
            'fb_pixel':    [PIXEL],
        },
        {
            'action.type': ['onsite_conversion'],
        },
        {
            'action.type':     ['post_interaction_gross'],
            'page':            [PAGE_ID],
            'post':            [post_id],
        },
        {
            'action.type': ['post_engagement'],
            'page':        [PAGE_ID],
            'post':        [post_id],
        },
        {
            'action.type': ['link_click'],
            'post':        [post_id],
            'post.wall':   [PAGE_ID],
        },
    ]


def patch_ad(ad_id, creative_id, post_id):
    url = '%s/%s' % (BASE, ad_id)
    tracking = build_tracking_specs(post_id)
    payload = {
        'creative':        json.dumps({'id': creative_id}),
        'tracking_specs':  json.dumps(tracking),
        'access_token':    TOKEN,
    }
    resp = requests.post(url, data=payload, timeout=30)
    data = resp.json()
    if data.get('success') or data.get('id'):
        print('  PATCH OK: ad %s -> creative %s (post %s)' % (ad_id[-6:], creative_id[-6:], post_id[-6:]))
        return True
    print('  PATCH ERRO ad %s: %s' % (ad_id[-6:], json.dumps(data, ensure_ascii=False)[:400]))
    return False


def main():
    print('\n=== PASSO 1: Mapear post IDs dos novos creatives ===')
    post_map = {}
    for ad_id, cr_id in AD_TO_CREATIVE.items():
        post_id = get_post_id(cr_id)
        post_map[ad_id] = (cr_id, post_id)
        print('  creative %s -> post_id=%s' % (cr_id[-6:], post_id))

    print('\n=== PASSO 2: PATCH nos ads com tracking_specs atualizados ===')
    results = []
    for ad_id, (cr_id, post_id) in post_map.items():
        if not post_id:
            print('  SKIP ad %s: post_id nao encontrado' % ad_id[-6:])
            results.append((ad_id, 'SKIP'))
            continue
        ok = patch_ad(ad_id, cr_id, post_id)
        results.append((ad_id, 'OK' if ok else 'FALHOU'))

    print('\n=== RESULTADO ===')
    for ad_id, status in results:
        print('  [%s] %s' % (status, ad_id))


if __name__ == '__main__':
    main()
