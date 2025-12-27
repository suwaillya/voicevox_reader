# VOICEVOX Reader（本機朗讀器 + RPG Maker MZ 對話朗讀插件）

VOICEVOX Reader 是一個在 Windows 上運行的本機文字轉語音朗讀工具。  
它可以：

- 將文字送到本機 VOICEVOX Engine 合成語音並播放
- 支援「中斷播放」：新句子會立即切掉舊句子
- 支援多個 Profile（例如不同遊戲）與角色語音設定
- 內建 GUI 編輯器可調整每個角色的 speaker / style / 語速 / 音高 / 抑揚 / 音量
- 提供 RPG Maker MZ 插件，可自動朗讀遊戲對話並支援「重播鍵（預設 F6）」


---

## ✅ 系統需求

### 作業系統
- Windows 10 / Windows 11

### 必要安裝
- ✅ **VOICEVOX Engine（必須安裝並開啟）**
- ❌ **不需要安裝 Python**

> 本工具會透過 `http://127.0.0.1:50021` 連線 VOICEVOX Engine。  
> 使用前請先啟動 VOICEVOX Engine（保持開著）。

---

## ✅ 下載方式（一般使用者）

請到 GitHub 專案的 **Releases** 頁面下載：

- `VoiceVoxReader.exe`

下載後直接執行即可。

---

## 🚀 使用方式（一般朗讀 / 設定角色）

### 1) 先啟動 VOICEVOX Engine
- 開啟 VOICEVOX Engine（桌面程式）
- 確認它正在執行（不要關掉）

### 2) 執行 VoiceVoxReader.exe
- 雙擊 `VoiceVoxReader.exe` 開啟 GUI

### 3) 測試朗讀
- 在 GUI 中選擇角色
- 點選「測試朗讀」
- 輸入文字 → 按 OK  
如果設定與 VOICEVOX Engine 正常，就會聽到語音播放。

---

## 🎛️ Profile / 角色設定說明

### Profile 是什麼？
Profile = 一組角色設定（通常對應一個遊戲）

例如：
- `default`
- `gameA`
- `gameB`

每個 Profile 都會有自己的角色表與聲音設定。

---

### 建立 Profile
1. GUI 上方 Profile 下拉選單旁點「New Profile」
2. 輸入 Profile 名稱（建議用遊戲名稱）
3. 完成後會自動切換到新 Profile

---

### 新增角色
1. 左側角色列表按「新增」
2. 輸入角色名稱（例如：莉莉 / 男主）
3. 右側可設定：
   - Speaker（人物）
   - Style（語氣）
   - 語速 / 音高 / 抑揚 / 音量

---

### 保存設定（重要）
- **保存當前角色設定**：只保存目前選中的角色到「記憶體」
- **保存所有角色設定**：寫入檔案（建議每次調完都按這個）

> 若沒有「保存所有角色設定」，關掉程式可能會丟失變更。

---

## 🎮 RPG Maker MZ：插件安裝與使用

本工具附帶 RPG Maker MZ 插件，可自動朗讀遊戲對話。

### 插件功能
- 讀取 RPG Maker MZ 對話框文字（Window_Message）
- 自動推送到本機 VOICEVOX Reader server
- 可自動解析說話者（speaker name）
- 支援重播鍵（預設 `F6`）

---

### 一鍵安裝插件（推薦）
1. 開啟 VoiceVoxReader.exe
2. 點選底部「安裝 Plugin 到遊戲」
3. 選擇遊戲根目錄（含 `js/` 資料夾的那層）
4. 程式會自動：
   - 複製 `VoiceVoxReader.js` 到 `<遊戲>/js/plugins/`
   - 修改 `<遊戲>/js/plugins.js` 啟用插件
   - 建立備份檔：`plugins.js.bak`
   - 自動建立 Profile = 遊戲資料夾名稱並切換

完成後，啟動遊戲即可自動朗讀對話。

---

### 插件重播鍵（Repeat Key）
預設是 `F6`

在對話出現時，按 `F6` 會重新朗讀上一句（並強制朗讀，即使同一句）。

---

## ⚠️ 注意事項 / 常見問題（FAQ）

---

### Q1：開啟程式時顯示 speakers load failed / Cannot load /speakers
✅ 原因：VOICEVOX Engine 沒有開啟或無法連線  
✅ 解法：
1. 先開啟 VOICEVOX Engine
2. 確認 VOICEVOX Engine API 是 `http://127.0.0.1:50021`
3. 再重新開啟 VoiceVoxReader.exe

---

### Q2：有朗讀請求但沒有聲音
可能原因：
- 音訊輸出裝置被設成錯誤裝置
- 系統音量或輸出裝置靜音
- VOICEVOX Engine 合成失敗

✅ 建議：
1. 確認 Windows 音量與輸出裝置
2. 在 GUI 使用「測試朗讀」是否可播放
3. 確認 VOICEVOX Engine 是否正常運作

---

### Q3：RPG Maker 遊戲沒有朗讀
✅ 檢查順序：
1. VoiceVoxReader.exe 有開著嗎？
2. VOICEVOX Engine 有開著嗎？
3. 遊戲 `js/plugins/VoiceVoxReader.js` 是否存在？
4. 遊戲 `js/plugins.js` 裡面有啟用 VoiceVoxReader 嗎？
5. 遊戲是否有防火牆阻擋本機連線（通常不會）

---

### Q4：安裝插件時提示「不是 RMMZ 遊戲？」
你選到的資料夾不是遊戲根目錄。

請確認你選的是含這些檔案的資料夾：
- `<GameRoot>/js/`
- `<GameRoot>/js/plugins/`
- `<GameRoot>/js/plugins.js`

---

### Q5：設定存檔在哪？
角色設定存在本工具的 `profiles/` 資料夾中：
- `profiles/<profile_name>/characters.json`


你可以用 GUI 底部按鈕「打開目前 Profile 資料夾」快速開啟。

---
### 其他問題
如有其他問題，請寄EMAIL至st33384049@gmail.com詢問

---


## 🧾 版本 / 更新
版本更新請查看 GitHub Releases 的更新記錄。

---

## 📌 免責聲明
本工具會修改遊戲的 `plugins.js` 以啟用插件，並建立備份檔 `plugins.js.bak`。  
請在操作前自行備份遊戲資料夾，本工具不對修改造成的損失負責。

---

## ❤️ 感謝
- VOICEVOX Engine：由 VOICEVOX 官方提供
- 本工具僅作為本機朗讀與整合用途

---

## 🪪 License
MIT License
