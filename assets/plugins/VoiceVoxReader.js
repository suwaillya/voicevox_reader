/*:
 * @target MZ
 * @plugindesc Send message text to local VOICEVOX reader server + Repeat key + Robust speaker parsing (v7)
 * @author You
 *
 * @param serverUrl
 * @text Server URL
 * @type string
 * @default http://127.0.0.1:5005/speak
 *
 * @param enabled
 * @text Enabled
 * @type boolean
 * @default true
 *
 * @param nameMode
 * @text Name Mode
 * @type select
 * @option auto
 * @option keep
 * @option stripFirstLine
 * @option stripPrefix
 * @default auto
 *
 * @param parseSpeakerFromFirstLine
 * @text Parse Speaker From First Line
 * @type boolean
 * @default true
 *
 * @param repeatEnabled
 * @text Enable Repeat Key
 * @type boolean
 * @default true
 *
 * @param repeatKey
 * @text Repeat Key
 * @type string
 * @default F6
 *
 * @help
 * v7:
 * - Fix bug: auto mode no longer strips the first line just because it is short.
 * - Now stripFirstLine only happens when:
 *     first line looks like a speaker name AND second line looks like dialogue.
 * - Prevents losing dialogue lines like:
 *     「おはようございます。\nお元気ですか」
 */

(() => {
  const pluginName = "VoiceVoxReader";
  const params = PluginManager.parameters(pluginName);

  const serverUrl = String(params.serverUrl || "http://127.0.0.1:5005/speak");
  const enabled = (String(params.enabled || "true") === "true");
  const nameMode = String(params.nameMode || "auto");
  const parseSpeakerFromFirstLine = (String(params.parseSpeakerFromFirstLine || "true") === "true");

  const repeatEnabled = (String(params.repeatEnabled || "true") === "true");
  const repeatKey = String(params.repeatKey || "F6").toUpperCase();

  let lastPayload = null;
  let lastSpeakTime = 0;
  const repeatCooldownMs = 300;

  function getSpeakerNameSafe() {
    try {
      if ($gameMessage && $gameMessage.speakerName) {
        const n = $gameMessage.speakerName();
        if (n && n.trim()) return n.trim();
      }
    } catch (e) {}
    try {
      if ($gameMessage && $gameMessage._speakerName) {
        const n = $gameMessage._speakerName;
        if (n && n.trim()) return n.trim();
      }
    } catch (e) {}
    return "";
  }

  function stripPrefixStyle(text) {
    const m = text.match(/^(.{1,20}?)[：:]\s*(.+)$/s);
    if (m) return m[2];
    return text;
  }

  // ---------- Speaker heuristics ----------
  function looksLikeDialogueLine(line) {
    if (!line) return false;
    const s = line.trim();
    if (!s) return false;

    // Dialogue often starts with quotes/brackets
    if (/^[「『（\(【\[]/.test(s)) return true;

    // Contains typical sentence-ending punctuations
    if (/[。！？\?!…]/.test(s)) return true;

    return false;
  }

  function looksLikeSpeakerName(line) {
    if (!line) return false;
    const s = line.trim();
    if (!s) return false;

    // Too long -> not name
    if (s.length > 20) return false;

    // If starts with dialogue symbols -> not name
    if (/^[「『（\(【\[]/.test(s)) return false;

    // If contains dialogue punctuations -> likely not a name
    if (/[。！？\?!…「『」』]/.test(s)) return false;

    // If has lots of spaces -> not typical name
    if (/\s{2,}/.test(s)) return false;

    return true;
  }

  // Parse speaker only when:
  // - first line looks like a name
  // - second line looks like dialogue (strong signal)
  function parseSpeakerFromText(text) {
    const lines = text.split(/\r?\n/);

    // Find first non-empty line as candidate speaker
    let idx = 0;
    while (idx < lines.length && lines[idx].trim().length === 0) idx++;
    if (idx >= lines.length) return { speaker: "", body: text };

    const first = lines[idx].trim();

    // Find next non-empty line as dialogue line
    let idx2 = idx + 1;
    while (idx2 < lines.length && lines[idx2].trim().length === 0) idx2++;
    const second = idx2 < lines.length ? lines[idx2].trim() : "";

    if (looksLikeSpeakerName(first) && looksLikeDialogueLine(second)) {
      // Remove only that speaker line (keep line breaks)
      const newLines = lines.slice(0, idx).concat(lines.slice(idx + 1));
      return { speaker: first, body: newLines.join("\n") };
    }

    return { speaker: "", body: text };
  }

  // ✅ FIXED: stripFirstLine only when it truly looks like "speaker name + dialogue"
  function stripFirstLineStyle(text) {
    const lines = text.split(/\r?\n/);
    if (lines.length <= 1) return text;

    // Find first non-empty line
    let idx = 0;
    while (idx < lines.length && lines[idx].trim().length === 0) idx++;
    if (idx >= lines.length) return text;

    const first = lines[idx].trim();

    // Find second non-empty line
    let idx2 = idx + 1;
    while (idx2 < lines.length && lines[idx2].trim().length === 0) idx2++;
    const second = idx2 < lines.length ? lines[idx2].trim() : "";

    // Only strip when it looks like speaker+dialogue
    if (looksLikeSpeakerName(first) && looksLikeDialogueLine(second)) {
      const newLines = lines.slice(0, idx).concat(lines.slice(idx + 1));
      return newLines.join("\n");
    }

    return text;
  }

  function applyNameMode(text) {
    if (!text) return text;
    if (nameMode === "keep") return text;
    if (nameMode === "stripPrefix") return stripPrefixStyle(text);
    if (nameMode === "stripFirstLine") return stripFirstLineStyle(text);

    // auto:
    // 1) try stripPrefix
    // 2) if unchanged, try stripFirstLine (NOW SAFE)
    let t = stripPrefixStyle(text);
    if (t !== text) return t;
    return stripFirstLineStyle(text);
  }

  function postSpeak(payload) {
    if (!enabled) return;
    if (!payload || !payload.text) return;

    lastPayload = payload;

    fetch(serverUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).catch(err => console.log("[VoiceVoxReader] fetch error:", err));
  }

  const _Window_Message_startMessage = Window_Message.prototype.startMessage;
  Window_Message.prototype.startMessage = function() {
    _Window_Message_startMessage.call(this);

    try {
      let rawText = $gameMessage.allText();
      if (!rawText || !rawText.trim()) return;

      let speaker = getSpeakerNameSafe();
      let speakerParsed = false;

      // If no native speaker name, try parse from first line (safe heuristics)
      if ((!speaker || !speaker.trim()) && parseSpeakerFromFirstLine) {
        const parsed = parseSpeakerFromText(rawText);
        if (parsed.speaker) {
          speaker = parsed.speaker;
          rawText = parsed.body;
          speakerParsed = true;
        }
      }

      // If speaker was parsed, do NOT strip first line again
      let text = speakerParsed ? stripPrefixStyle(rawText) : applyNameMode(rawText);
      text = (text || "").trim();
      if (!text) return;

      if (!speaker || !speaker.trim()) speaker = "default";

      postSpeak({ name: speaker, text, interrupt: true });

    } catch (e) {
      console.log("[VoiceVoxReader] error:", e);
    }
  };

  // repeat via Input
  const keyMap = Object.assign({}, Input.keyMapper);
  const functionKeyCodes = {
    "F1":112,"F2":113,"F3":114,"F4":115,"F5":116,"F6":117,
    "F7":118,"F8":119,"F9":120,"F10":121,"F11":122,"F12":123
  };

  if (functionKeyCodes[repeatKey]) {
    keyMap[functionKeyCodes[repeatKey]] = "vv_repeat";
  } else {
    const ch = repeatKey.length === 1 ? repeatKey : "";
    if (ch) keyMap[ch.charCodeAt(0)] = "vv_repeat";
  }
  Input.keyMapper = keyMap;

  const _Scene_Map_update = Scene_Map.prototype.update;
  Scene_Map.prototype.update = function() {
    _Scene_Map_update.call(this);
    if (!repeatEnabled || !lastPayload) return;

    if (Input.isTriggered("vv_repeat")) {
      const now = Date.now();
      if (now - lastSpeakTime < repeatCooldownMs) return;
      lastSpeakTime = now;

      postSpeak({ ...lastPayload, interrupt: true, no_dedup: true });
    }
  };

})();
