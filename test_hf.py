import urllib.request
import json

url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
req = urllib.request.Request(url, method="POST")
req.add_header("Content-Type", "application/json")
# No auth needed just to see if we get a 401 instead of a DNS error
data = json.dumps({"inputs": "test"}).encode('utf-8')

try:
    with urllib.request.urlopen(req, data=data) as response:
        print(response.status)
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.reason)
except Exception as e:
    print("Error:", e)
