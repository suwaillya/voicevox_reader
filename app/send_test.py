import requests
import time

URL = "http://127.0.0.1:5005/speak"

tests = [
    {"name": "default", "text": "これはデフォルトです。"},
    {"name": "莉莉", "text": "私はリリィです。"},
    {"name": "男主", "text": "僕は主人公です。"}
]

for t in tests:
    requests.post(URL, json=t)
    time.sleep(0.2)

print("sent")
