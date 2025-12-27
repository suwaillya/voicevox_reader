# app/gui.py
from __future__ import annotations
import os
import sys
import json
import requests
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter import filedialog
import shutil
import re

SERVER = "http://127.0.0.1:5005"

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
PROFILES_ROOT = os.path.join(PROJECT_ROOT, "profiles")

DEFAULT_PROFILE_TEMPLATE = {
    "default": {
        "style_id": 2,
        "voice_params": {
            "speedScale": 1.0,
            "pitchScale": 0.0,
            "intonationScale": 1.0,
            "volumeScale": 1.0
        }
    }
}


# ----------------- PyInstaller resource helper -----------------
def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource.
    Works for:
      - dev mode (python app/main.py)
      - PyInstaller onefile mode (sys._MEIPASS)
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS  # type: ignore
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)


# ----------------- File helpers -----------------
def ensure_profile_file(profile_name: str) -> str:
    pdir = os.path.join(PROFILES_ROOT, profile_name)
    os.makedirs(pdir, exist_ok=True)
    path = os.path.join(pdir, "characters.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PROFILE_TEMPLATE, f, ensure_ascii=False, indent=2)
    return path


def load_characters(profile_name: str) -> dict:
    path = ensure_profile_file(profile_name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_characters(profile_name: str, data: dict):
    path = ensure_profile_file(profile_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ----------------- VOICEVOX speakers helpers -----------------
def fetch_speakers() -> list:
    r = requests.get(f"{SERVER}/speakers", timeout=5)
    r.raise_for_status()
    return r.json()


def build_speaker_maps(speakers: list):
    speaker_names = []
    speaker_to_styles = {}
    style_id_to_pair = {}

    for sp in speakers:
        sname = sp.get("name", "")
        speaker_names.append(sname)
        styles = []
        for st in sp.get("styles", []):
            stname = st.get("name", "")
            stid = st.get("id", None)
            if stid is None:
                continue
            styles.append((stname, int(stid)))
            style_id_to_pair[int(stid)] = (sname, stname)
        speaker_to_styles[sname] = styles

    speaker_names.sort()
    return speaker_names, speaker_to_styles, style_id_to_pair


# ----------------- GUI -----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VOICEVOX Reader - Profile & Character Config (GUI v3)")
        self.geometry("980x560")

        self.current_profile = tk.StringVar(value="default")
        self.characters_data: dict = {}
        self.selected_character = tk.StringVar(value="default")

        # dirty flags
        self.dirty_current = False  # current editor differs from in-memory character data
        self.dirty_all = False      # in-memory differs from file (needs save to JSON)

        # voicevox speaker data
        self.speaker_names = []
        self.speaker_to_styles = {}
        self.style_id_to_pair = {}

        # UI vars
        self.speaker_var = tk.StringVar(value="")
        self.style_var = tk.StringVar(value="")
        self.style_id_var = tk.IntVar(value=2)  # internal only; not shown

        self.speed_var = tk.DoubleVar(value=1.0)
        self.pitch_var = tk.DoubleVar(value=0.0)
        self.intonation_var = tk.DoubleVar(value=1.0)
        self.volume_var = tk.DoubleVar(value=1.0)

        # build UI
        self._build_topbar()
        self._build_main_area()
        self._build_bottom_bar()

        # load speakers once (no refresh button)
        self.load_speakers_once()

        # initial load
        self.refresh_profiles()
        self.load_profile(self.current_profile.get())

        # watch changes (mark dirty)
        self._bind_dirty_watchers()

    # ---------------- UI ----------------
    def _build_topbar(self):
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(frame, text="Profile:").pack(side="left")

        self.profile_combo = ttk.Combobox(frame, textvariable=self.current_profile, state="readonly", width=28)
        self.profile_combo.pack(side="left", padx=6)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_changed)

        ttk.Button(frame, text="Refresh Profiles", command=self.refresh_profiles).pack(side="left", padx=6)
        ttk.Button(frame, text="New Profile", command=self.create_profile).pack(side="left", padx=6)

        self.profile_status = ttk.Label(frame, text="")
        self.profile_status.pack(side="right")

    def _build_main_area(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        # left: character list
        left = ttk.Frame(container)
        left.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(left, text="角色列表").pack(anchor="w")

        self.char_listbox = tk.Listbox(left, height=22, width=28)
        self.char_listbox.pack(fill="y", expand=False, pady=6)
        self.char_listbox.bind("<<ListboxSelect>>", self.on_select_character)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x", pady=6)
        ttk.Button(btn_row, text="新增", command=self.add_character).pack(side="left", padx=4)
        ttk.Button(btn_row, text="刪除", command=self.delete_character).pack(side="left", padx=4)

        # right: editor
        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(right, text="角色設定", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        self.char_title = ttk.Label(right, text="(none)", font=("Segoe UI", 14, "bold"))
        self.char_title.grid(row=1, column=0, sticky="w", pady=(2, 10))

        form = ttk.Frame(right)
        form.grid(row=2, column=0, sticky="nsew")

        ttk.Label(form, text="人物 (Speaker)").grid(row=0, column=0, sticky="e", padx=8, pady=8)
        self.speaker_combo = ttk.Combobox(form, textvariable=self.speaker_var, state="readonly", width=26)
        self.speaker_combo.grid(row=0, column=1, sticky="w", pady=8)
        self.speaker_combo.bind("<<ComboboxSelected>>", self.on_speaker_changed)

        ttk.Label(form, text="語氣 (Style)").grid(row=1, column=0, sticky="e", padx=8, pady=8)
        self.style_combo = ttk.Combobox(form, textvariable=self.style_var, state="readonly", width=26)
        self.style_combo.grid(row=1, column=1, sticky="w", pady=8)
        self.style_combo.bind("<<ComboboxSelected>>", self.on_style_changed)

        # Sliders (Chinese labels + values on label)
        self._add_slider_block(form, "語速", self.speed_var, 0.5, 2.0, row=2)
        self._add_slider_block(form, "音高", self.pitch_var, -0.5, 0.5, row=3)
        self._add_slider_block(form, "抑揚", self.intonation_var, 0.0, 2.0, row=4)
        self._add_slider_block(form, "音量", self.volume_var, 0.0, 2.0, row=5)

        # buttons
        btns = ttk.Frame(right)
        btns.grid(row=3, column=0, sticky="w", pady=12)

        self.btn_save_current = ttk.Button(btns, text="保存當前角色設定", command=self.save_current_character)
        self.btn_save_current.pack(side="left", padx=6)

        self.btn_test = ttk.Button(btns, text="測試朗讀", command=self.test_speak)
        self.btn_test.pack(side="left", padx=6)

        self.btn_save_all = ttk.Button(btns, text="保存所有角色設定", command=self.save_current_profile)
        self.btn_save_all.pack(side="left", padx=6)

        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

    def _add_slider_block(self, parent, zh_label, var, minv, maxv, row):
        value_label = ttk.Label(parent, text=f"{zh_label}: {var.get():.2f}", font=("Segoe UI", 10))
        value_label.grid(row=row, column=0, sticky="e", padx=8, pady=8)

        scale = ttk.Scale(parent, variable=var, from_=minv, to=maxv, orient="horizontal", length=320)
        scale.grid(row=row, column=1, sticky="w", pady=8)

        def update_label(*_):
            value_label.config(text=f"{zh_label}: {var.get():.2f}")
        var.trace_add("write", update_label)
        update_label()

    def _build_bottom_bar(self):
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=10, pady=8)

        ttk.Button(frame, text="打開目前 Profile 資料夾", command=self.open_profile_folder).pack(side="left")
        ttk.Button(frame, text="顯示目前 Profile(API)", command=self.show_current_profile_api).pack(side="left", padx=8)

        ttk.Separator(frame, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(frame, text="安裝 Plugin 到遊戲", command=self.install_plugin_to_game).pack(side="left")

        self.status = ttk.Label(frame, text="Ready")
        self.status.pack(side="right")

    # ---------------- Dirty handling ----------------
    def mark_dirty_current(self):
        self.dirty_current = True
        self.dirty_all = True
        self.update_dirty_ui()

    def clear_dirty_current(self):
        self.dirty_current = False
        self.update_dirty_ui()

    def clear_dirty_all(self):
        self.dirty_all = False
        self.update_dirty_ui()

    def update_dirty_ui(self):
        # Add '*' prefix if dirty
        cur_text = "保存當前角色設定"
        all_text = "保存所有角色設定"

        if self.dirty_current:
            cur_text = "* " + cur_text
        if self.dirty_all:
            all_text = "* " + all_text

        self.btn_save_current.config(text=cur_text)
        self.btn_save_all.config(text=all_text)

    def _bind_dirty_watchers(self):
        # Any change on editor fields should mark dirty_current
        self.speaker_var.trace_add("write", lambda *_: self.mark_dirty_current())
        self.style_var.trace_add("write", lambda *_: self.mark_dirty_current())
        self.speed_var.trace_add("write", lambda *_: self.mark_dirty_current())
        self.pitch_var.trace_add("write", lambda *_: self.mark_dirty_current())
        self.intonation_var.trace_add("write", lambda *_: self.mark_dirty_current())
        self.volume_var.trace_add("write", lambda *_: self.mark_dirty_current())

    # ---------------- Logic ----------------
    def status_set(self, msg: str):
        self.status.config(text=msg)

    def load_speakers_once(self):
        try:
            speakers_raw = fetch_speakers()
            self.speaker_names, self.speaker_to_styles, self.style_id_to_pair = build_speaker_maps(speakers_raw)
            self.speaker_combo["values"] = self.speaker_names
            if self.speaker_names and not self.speaker_var.get():
                self.speaker_var.set(self.speaker_names[0])
            self.status_set(f"Speakers loaded: {len(self.speaker_names)}")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot load /speakers: {e}")
            self.status_set("Speakers load failed")

    def refresh_profiles(self):
        try:
            r = requests.get(f"{SERVER}/profile/list", timeout=3)
            data = r.json()
            profiles = data.get("profiles", [])
            if not profiles:
                profiles = ["default"]
            self.profile_combo["values"] = profiles
            if self.current_profile.get() not in profiles:
                self.current_profile.set(profiles[0])
            self.profile_status.config(text=f"{len(profiles)} profiles")
            self.status_set("Profiles refreshed")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot reach server: {e}")
            self.status_set("Server not reachable")

    def on_profile_changed(self, event=None):
        prof = self.current_profile.get()
        self.load_profile(prof)

    def create_profile(self):
        name = simpledialog.askstring("New Profile", "Enter new profile name:")
        if not name:
            return
        name = name.strip()
        if not name:
            return
        ensure_profile_file(name)

        try:
            requests.post(f"{SERVER}/profile/load", json={"profile": name}, timeout=3)
        except:
            pass

        self.refresh_profiles()
        self.current_profile.set(name)
        self.load_profile(name)

    def load_profile(self, profile_name: str):
        # warn if unsaved changes
        if self.dirty_all:
            if not messagebox.askyesno("未保存變更", "你有尚未保存的設定變更，切換 Profile 會丟失它們。\n仍要切換嗎？"):
                return

        # switch backend profile
        try:
            requests.post(f"{SERVER}/profile/load", json={"profile": profile_name}, timeout=3)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot load profile via server: {e}")
            return

        # load local file
        self.characters_data = load_characters(profile_name)
        self.populate_character_list()
        self.status_set(f"Profile loaded: {profile_name}")

        # reset dirty flags
        self.dirty_current = False
        self.dirty_all = False
        self.update_dirty_ui()

    def populate_character_list(self):
        self.char_listbox.delete(0, tk.END)
        names = sorted(self.characters_data.keys(), key=lambda x: (x != "default", x))
        for n in names:
            self.char_listbox.insert(tk.END, n)

        if "default" in self.characters_data:
            idx = names.index("default")
            self.char_listbox.selection_set(idx)
            self.char_listbox.activate(idx)
            self.on_select_character()

    def on_select_character(self, event=None):
        sel = self.char_listbox.curselection()
        if not sel:
            return

        # warn if current editor dirty
        if self.dirty_current:
            if not messagebox.askyesno("尚未保存角色設定", "你有尚未保存的角色變更，切換角色會丟失它。\n仍要切換嗎？"):
                return

        name = self.char_listbox.get(sel[0])
        self.selected_character.set(name)
        self.char_title.config(text=name)

        prof = self.characters_data.get(name, {})
        style_id = int(prof.get("style_id", 2))
        self.style_id_var.set(style_id)

        # resolve speaker/style by style_id
        if style_id in self.style_id_to_pair:
            sp, st = self.style_id_to_pair[style_id]
            self.speaker_var.set(sp)
            self._populate_style_combo(sp)
            self.style_var.set(st)
        else:
            if self.speaker_names:
                self.speaker_var.set(self.speaker_names[0])
                self._populate_style_combo(self.speaker_names[0])

        vp = prof.get("voice_params", {})
        default_vp = self.characters_data.get("default", {}).get("voice_params", {})

        self.speed_var.set(float(vp.get("speedScale", default_vp.get("speedScale", 1.0))))
        self.pitch_var.set(float(vp.get("pitchScale", default_vp.get("pitchScale", 0.0))))
        self.intonation_var.set(float(vp.get("intonationScale", default_vp.get("intonationScale", 1.0))))
        self.volume_var.set(float(vp.get("volumeScale", default_vp.get("volumeScale", 1.0))))

        # selecting character resets current dirty flag
        self.dirty_current = False
        self.update_dirty_ui()

    def _populate_style_combo(self, speaker_name: str):
        styles = self.speaker_to_styles.get(speaker_name, [])
        style_names = [s[0] for s in styles]
        self.style_combo["values"] = style_names
        if style_names:
            self.style_var.set(style_names[0])
            self.on_style_changed()

    def on_speaker_changed(self, event=None):
        sp = self.speaker_var.get()
        self._populate_style_combo(sp)

    def on_style_changed(self, event=None):
        sp = self.speaker_var.get()
        st = self.style_var.get()
        styles = self.speaker_to_styles.get(sp, [])
        for (style_name, style_id) in styles:
            if style_name == st:
                self.style_id_var.set(int(style_id))
                return

    def add_character(self):
        name = simpledialog.askstring("新增角色", "角色名稱：")
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.characters_data:
            messagebox.showwarning("已存在", f"'{name}' 已存在。")
            return

        self.characters_data[name] = {
            "style_id": int(self.style_id_var.get()),
            "voice_params": {}
        }
        self.populate_character_list()
        self.status_set(f"Added character: {name}")
        self.mark_dirty_current()

    def delete_character(self):
        name = self.selected_character.get()
        if not name:
            return
        if name == "default":
            messagebox.showwarning("不允許", "不能刪除 default")
            return
        if messagebox.askyesno("確認", f"刪除角色 '{name}'？"):
            self.characters_data.pop(name, None)
            self.populate_character_list()
            self.status_set(f"Deleted: {name}")
            self.mark_dirty_current()

    def save_current_character(self):
        name = self.selected_character.get()
        if not name:
            return

        if name not in self.characters_data:
            self.characters_data[name] = {}

        self.characters_data[name]["style_id"] = int(self.style_id_var.get())
        self.characters_data[name]["voice_params"] = {
            "speedScale": float(self.speed_var.get()),
            "pitchScale": float(self.pitch_var.get()),
            "intonationScale": float(self.intonation_var.get()),
            "volumeScale": float(self.volume_var.get())
        }

        self.status_set(f"Saved current character settings: {name}")
        # current editor synced with in-memory, so clear current dirty
        self.clear_dirty_current()

        # BUT still needs saving to file, so keep dirty_all as-is
        self.dirty_all = True
        self.update_dirty_ui()

    def test_speak(self):
        name = self.selected_character.get() or "default"
        text = simpledialog.askstring("測試朗讀", "輸入要朗讀的文字：", initialvalue="こんにちは。テストです。")
        if not text:
            return

        payload = {
            "name": name,
            "text": text,
            "style_id": int(self.style_id_var.get()),
            "voice_params": {
                "speedScale": float(self.speed_var.get()),
                "pitchScale": float(self.pitch_var.get()),
                "intonationScale": float(self.intonation_var.get()),
                "volumeScale": float(self.volume_var.get())
            }
        }

        try:
            r = requests.post(f"{SERVER}/speak", json=payload, timeout=3)
            if r.status_code == 200:
                self.status_set("已加入朗讀隊列")
            else:
                self.status_set("朗讀失敗")
                messagebox.showerror("Error", r.text)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot reach server: {e}")

    def save_current_profile(self):
        # Save current editor into current character first (safety)
        self.save_current_character()

        profile_name = self.current_profile.get()
        if "default" not in self.characters_data:
            self.characters_data["default"] = DEFAULT_PROFILE_TEMPLATE["default"]

        save_characters(profile_name, self.characters_data)
        self.status_set(f"Saved all settings: profiles/{profile_name}/characters.json")

        # reload backend profile to apply immediately
        try:
            requests.post(f"{SERVER}/profile/load", json={"profile": profile_name}, timeout=3)
        except:
            pass

        # file saved -> clear all dirty flags
        self.dirty_current = False
        self.dirty_all = False
        self.update_dirty_ui()

    def open_profile_folder(self):
        profile_name = self.current_profile.get()
        pdir = os.path.join(PROFILES_ROOT, profile_name)
        os.makedirs(pdir, exist_ok=True)
        try:
            os.startfile(pdir)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_current_profile_api(self):
        try:
            r = requests.get(f"{SERVER}/profile/current", timeout=3)
            messagebox.showinfo("目前 Profile", r.text)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def install_plugin_to_game(self):
        """
        Ask user to select RMMZ game root folder, then:
          1) copy assets/plugins/VoiceVoxReader.js -> <GameRoot>/js/plugins/
          2) patch <GameRoot>/js/plugins.js to enable plugin
          3) backup plugins.js -> plugins.js.bak
          4) auto create / switch profile to game folder name
        """
        game_root = filedialog.askdirectory(title="選擇遊戲根目錄（含 js 資料夾）")
        if not game_root:
            return

        js_dir = os.path.join(game_root, "js")
        plugins_dir = os.path.join(js_dir, "plugins")
        plugins_js = os.path.join(js_dir, "plugins.js")

        # Check structure
        if not os.path.isdir(js_dir) or not os.path.isdir(plugins_dir) or not os.path.isfile(plugins_js):
            messagebox.showerror(
                "不是 RMMZ 遊戲？",
                "找不到必要檔案：\n"
                "- <GameRoot>/js/\n"
                "- <GameRoot>/js/plugins/\n"
                "- <GameRoot>/js/plugins.js\n\n"
                "請確認你選的是遊戲根目錄。"
            )
            return

        # Confirm
        plugin_dst = os.path.join(plugins_dir, "VoiceVoxReader.js")
        bak_path = plugins_js + ".bak"

        msg = (
            "即將對遊戲資料夾進行修改（建議你先備份遊戲）：\n\n"
            f"1) 複製 Plugin 檔案：\n   {plugin_dst}\n\n"
            f"2) 修改 plugins.js 以啟用 Plugin：\n   {plugins_js}\n\n"
            f"3) 建立備份（若存在則覆蓋）：\n   {bak_path}\n\n"
            "⚠️ 注意：修改遊戲檔案可能導致遊戲無法啟動或存檔異常。\n"
            "請確定你願意承擔風險。\n\n"
            "是否繼續安裝？"
        )

        if not messagebox.askyesno("確認安裝 Plugin", msg):
            return

        try:
            # 1) copy plugin file
            os.makedirs(plugins_dir, exist_ok=True)

            template_path = resource_path(os.path.join("assets", "plugins", "VoiceVoxReader.js"))
            if not os.path.isfile(template_path):
                messagebox.showerror("缺少模板", f"找不到 Plugin 模板檔案：\n{template_path}")
                return

            shutil.copyfile(template_path, plugin_dst)

            # 2) backup plugins.js
            shutil.copyfile(plugins_js, bak_path)

            # 3) patch plugins.js
            self._patch_plugins_js(plugins_js)

            # 4) auto create & switch profile
            game_name = os.path.basename(os.path.abspath(game_root))
            ensure_profile_file(game_name)

            self.refresh_profiles()
            self.current_profile.set(game_name)
            self.load_profile(game_name)

            messagebox.showinfo("成功", f"Plugin 已安裝完成！\nProfile 已建立並切換：{game_name}\n\n請到遊戲內測試對話朗讀。")
            self.status_set("Plugin installed successfully")

        except Exception as e:
            messagebox.showerror("安裝失敗", str(e))

    def _patch_plugins_js(self, plugins_js_path: str):
        """
        Safe patch for RPG Maker MZ plugins.js.
        Strategy:
          1) Find 'var $plugins = [...] ;'
          2) Extract the array text
          3) Convert to JSON and parse
          4) Update/append VoiceVoxReader entry
          5) Write back
        """
        import json
        import re

        with open(plugins_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Match: var $plugins = [ ... ];
        m = re.search(r"(var\s+\$plugins\s*=\s*)(\[\s*.*?\s*\])(\s*;)", content, flags=re.S)
        if not m:
            raise RuntimeError("無法找到 var $plugins = [...] 結構，可能此遊戲修改過 plugins.js。")

        prefix = m.group(1)
        array_text = m.group(2)
        suffix = m.group(3)

        # Parse the array as JSON
        # array_text is usually valid JSON already.
        try:
            plugins_list = json.loads(array_text)
        except Exception as e:
            # Try minor fixes: remove trailing commas
            fixed = re.sub(r",\s*([\]\}])", r"\1", array_text)
            plugins_list = json.loads(fixed)

        if not isinstance(plugins_list, list):
            raise RuntimeError("$plugins 不是 list，無法處理。")

        new_entry = {
            "name": "VoiceVoxReader",
            "status": True,
            "description": "",
            "parameters": {
                "serverUrl": "http://127.0.0.1:5005/speak",
                "enabled": "true",
                "nameMode": "auto",
                "repeatEnabled": "true",
                "repeatKey": "F6"
            }
        }

        updated = False
        for i, it in enumerate(plugins_list):
            if isinstance(it, dict) and it.get("name") == "VoiceVoxReader":
                plugins_list[i] = new_entry
                updated = True
                break

        if not updated:
            plugins_list.append(new_entry)

        # Dump back as JSON (RMMZ accepts JSON)
        new_array_text = json.dumps(plugins_list, ensure_ascii=False, indent=2)

        new_content = content[:m.start()] + prefix + new_array_text + suffix + content[m.end():]

        with open(plugins_js_path, "w", encoding="utf-8") as f:
            f.write(new_content)


if __name__ == "__main__":
    App().mainloop()
