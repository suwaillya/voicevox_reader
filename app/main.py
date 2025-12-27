# app/main.py
from __future__ import annotations
import threading
import time
import requests
import sys
import os

from server import start_server
from gui import App

SERVER = "http://127.0.0.1:5005"


def wait_server_ready(timeout=8.0):
    """Wait until Flask server responds."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = requests.get(SERVER + "/health", timeout=0.5)
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.2)
    return False


def main():
    # 你可以在這裡設定預設 profile
    default_profile = "default"

    # 1) start server in background thread
    th = threading.Thread(
        target=start_server,
        kwargs={"profile": default_profile, "host": "127.0.0.1", "port": 5005},
        daemon=True
    )
    th.start()

    # 2) wait server ready
    ok = wait_server_ready()
    if not ok:
        print("[Main] Server failed to start.")
        return

    # 3) start GUI
    app = App()
    app.mainloop()

    # GUI 關閉後即退出
    print("[Main] GUI closed, exiting.")


if __name__ == "__main__":
    main()
