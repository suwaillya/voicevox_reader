import requests

requests.post("http://127.0.0.1:5005/profile/load", json={"profile": "gameB"})
print("switched to gameB")
