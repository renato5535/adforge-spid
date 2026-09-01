import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

token = os.getenv('META_ACCESS_TOKEN')

# Pegar URL do criativo do B-00 (mais confiavel, RMKT)
creative_id = '1968014820481583'
url = f'https://graph.facebook.com/v25.0/{creative_id}?fields=id,name,object_story_spec,asset_feed_spec,link_url,body,title&access_token={token}'
req = urllib.request.urlopen(url)
d = json.loads(req.read())
print(json.dumps(d, indent=2, ensure_ascii=False))
