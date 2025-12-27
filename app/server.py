# app/server.py
from __future__ import annotations
import os
import argparse
from flask import Flask, request, jsonify

from queue_manager import SpeechQueueManager
from profile_manager import ProfileManager

app = Flask(__name__)

# ====== Default settings ======
VOICEVOX_URL = "http://127.0.0.1:50021"
DEDUP_ENABLED = True
MAX_QUEUE_SIZE = 100

# Profiles live at project_root/profiles
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
PROFILES_ROOT = os.path.join(PROJECT_ROOT, "profiles")

profile_mgr = ProfileManager(PROFILES_ROOT)

# Current loaded profile (runtime)
CURRENT_PROFILE = "default"

# Manager instance
manager: SpeechQueueManager = None  # type: ignore


# ---- Parse CLI args (only when running as main) ----
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="default", help="profile name under profiles/")
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", default=5005, type=int, help="bind port")
    return parser.parse_args()


def create_manager(profile_name: str) -> SpeechQueueManager:
    characters_path = profile_mgr.ensure_profile(profile_name)
    mgr = SpeechQueueManager(
        voicevox_url=VOICEVOX_URL,
        characters_path=characters_path,
        dedup_enabled=DEDUP_ENABLED,
        max_queue_size=MAX_QUEUE_SIZE,
    )
    mgr.start()
    return mgr


# ------------------ API ------------------
@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/speakers")
def speakers():
    try:
        data = manager.client.get_speakers()
        return jsonify(data)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/profile/current")
def profile_current():
    return jsonify({
        "ok": True,
        "profile": CURRENT_PROFILE,
        "characters_path": manager.get_current_characters_path()
    })


@app.get("/profile/list")
def profile_list():
    return jsonify({
        "ok": True,
        "profiles": profile_mgr.list_profiles()
    })


@app.post("/profile/load")
def profile_load():
    """
    Switch profile at runtime.
    Body:
      { "profile": "gameA" }
    """
    global CURRENT_PROFILE
    data = request.get_json(force=True, silent=True) or {}
    prof = (data.get("profile") or "").strip()

    if not prof:
        return jsonify({"ok": False, "reason": "missing_profile"}), 400

    # Ensure profile exists (auto-create if missing)
    characters_path = profile_mgr.ensure_profile(prof)

    # Stop + clear before switching (recommended)
    manager.stop_current()
    manager.clear_queue()
    manager.load_characters_path(characters_path)

    CURRENT_PROFILE = prof
    return jsonify({
        "ok": True,
        "profile": CURRENT_PROFILE,
        "characters_path": characters_path
    })


@app.post("/speak")
def speak():
    """
    POST body:
      {
        "name": "莉莉",
        "text": "こんにちは！",
        "style_id": 2,            (optional override)
        "voice_params": {...},    (optional override)
        "interrupt": true,        (optional)  新句子來就切掉舊的
        "no_dedup": true          (optional)  強制朗讀，即使同一句
      }
    """
    data = request.get_json(force=True, silent=True) or {}

    text = (data.get("text") or "").strip()
    name = (data.get("name") or "default").strip()

    style_id = data.get("style_id", None)
    voice_params = data.get("voice_params", None)

    interrupt = bool(data.get("interrupt", False))
    no_dedup = bool(data.get("no_dedup", False))

    if interrupt:
        ok = manager.enqueue_interrupt(
            text=text,
            name=name,
            style_id=style_id,
            voice_params=voice_params,
            no_dedup=no_dedup
        )
    else:
        ok = manager.enqueue(
            text=text,
            name=name,
            style_id=style_id,
            voice_params=voice_params,
            no_dedup=no_dedup
        )

    if ok:
        return jsonify({"ok": True})
    else:
        return jsonify({"ok": False, "reason": "empty_or_queue_full"}), 400


@app.post("/stop")
def stop():
    manager.stop_current()
    return jsonify({"ok": True})


@app.post("/clear")
def clear():
    manager.clear_queue()
    return jsonify({"ok": True})


# ------------------ Start functions ------------------
def start_server(profile: str = "default", host: str = "127.0.0.1", port: int = 5005):
    """
    Start server programmatically (for main.py / GUI launcher).
    Does NOT parse argv.
    """
    global manager, CURRENT_PROFILE

    CURRENT_PROFILE = profile

    # Create manager with selected profile
    manager = create_manager(CURRENT_PROFILE)

    # IMPORTANT: use_reloader=False to avoid running twice in thread mode
    app.run(host=host, port=port, debug=False, use_reloader=False)


def main():
    """
    CLI entry:
      python server.py --profile default
    """
    args = parse_args()
    start_server(profile=args.profile, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
