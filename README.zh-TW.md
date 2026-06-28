<!-- Translated from README.md @ 0cba4c6. Translations may lag behind English. PRs welcome. -->
[English](README.md) · **繁體中文** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md)

# youtube-to-yoto

把任何 YouTube 播放清單轉換為 [Yoto](https://yotoplay.com/) MYO（「Make Your Own」）卡片播放清單，並為每一集在播放器的 LED 矩陣上顯示專屬的 16×16 像素藝術圖示。

以 [Claude Code](https://claude.ai/code) skill / plugin 的形式建構。v1 僅支援 Mac。

## 功能說明

你提供一個 YouTube 播放清單的 URL，它會：

1. 下載每部影片的音訊為 MP3。
2. 轉錄每集前 3 分鐘的內容（本地 Whisper，免費，無需 API 呼叫）。
3. 透過 Claude SubAgents 為每集挑選一個可繪製的具體名詞（例如 `rhinoceros beetle`、`birthday cake`）。
4. 透過 Claude SubAgents 為每個獨特名詞設計一個 16×16 像素藝術精靈圖。
5. 將所有內容（音訊 + 精靈圖 + 播放清單元資料）上傳至你的 Yoto 帳號。
6. 提示你在播放器上點擊一張空白 MYO 卡片以完成綁定。

約 100 集的總實際耗時：約 1.5 小時。

## 費用

> 在安裝之前請先閱讀本節。

此 skill 使用 Claude SubAgents 設計像素藝術圖示。費用取決於**你使用 Claude 的計費方式**：

| 計費方式 | 你的費用 |
|---|---|
| **Claude Pro / Max 訂閱** *（推薦）* | 不額外收費。SubAgent 執行次數從你現有的方案配額中扣除。100 集的播放清單通常在 Max 一個工作階段內即可完成。 |
| **按量計費 API 金鑰** | 每個獨特精靈圖約 $0.10–0.15（Opus）。100 集播放清單含約 70 個獨特主題 ≈ **$7–$10**。 |
| **Claude 免費方案** | 配額不足 — 請在執行前升級至 Pro。 |

此 skill **每次執行前都會公告預估費用**，並請你確認後才會展開 SubAgents。部分進度會被快取，可隨時繼續。

詳細資訊：[docs/COSTS.md](docs/COSTS.md)。

## 硬體需求

| 元件 | 最低配置 | 建議配置 |
|---|---|---|
| macOS | 12 Monterey | 14 Sonoma+ |
| CPU | Intel Mac（慢 3–5 倍） | **Apple Silicon（M1+）** — whisper.cpp 使用 Metal GPU 加速；turbo 在 M1 上約達 15 倍實時速度 |
| RAM | 8 GB | 16 GB（Whisper 尖峰時使用 2–3 GB） |
| 可用磁碟空間 | 4 GB | 10 GB |
| 網路 | 穩定寬頻 | 100 集下載約 800 MB；上傳至 Yoto 約 800 MB |
| 實際耗時 | — | 100 集首次執行約 1.5 小時 |

**v1 不支援 Windows 和 Linux。**

## 磁碟空間

| 項目 | 大小 | 時機 |
|---|---|---|
| Whisper `large-v3-turbo` 模型 | **1.5 GB** | 一次性，所有播放清單共用 |
| brew 套件（yt-dlp、ffmpeg、whisper-cpp、node） | 約 400 MB | 一次性 |
| pip 套件（Pillow、requests、aiomqtt） | 約 60 MB | 一次性 |
| `pixel-art` skill | 約 2 MB | 一次性 |
| 每個播放清單的 MP3 音訊 | 約 8 MB / 集 | 每個播放清單。上傳後可刪除。100 集 ≈ 800 MB。 |
| 轉錄文字、精靈圖、快取 | 總計 < 5 MB | 可忽略不計 |

**首次執行總計：約 2.5 GB 一次性 + 每個播放清單約 1 GB。**

## 相依套件（及用途）

所有所需的外部工具及其用途：

| 相依套件 | 用途 | 是否必要？ |
|---|---|---|
| **yt-dlp** | 從 YouTube 下載音訊。YouTube 沒有官方的音訊下載 API。 | 必要 |
| **ffmpeg** | yt-dlp 在內部使用它從 YouTube 串流中提取 MP3。也用於切割 3 分鐘 WAV 供 Whisper 使用。 | 必要 |
| **whisper-cpp** + `ggml-large-v3-turbo` 模型 | 轉錄每集前 3 分鐘，讓 Claude 知道該畫哪個具體名詞作為圖示。「Episode 5: Friends」這類 YouTube 標題無法告訴我們主題。 | 選用 — 當 YouTube 標題已夠具體、足以辨識主題時，skill 會跳過第 2 階段 |
| **node** | （1）yt-dlp 使用 Node 作為 JS 執行環境，以解決 YouTube 的反機器人挑戰。（2）`npx skills` 用於安裝 `pixel-art` skill。 | 必要 |
| **Pillow**（pip） | 讀寫 16×16 PNG 精靈圖 | 必要 |
| **requests**（pip） | Yoto REST API 的 HTTP 用戶端 | 必要 |
| **aiomqtt**（pip） | `mqtt_log.py` 診斷工具的非同步 MQTT 用戶端 | 選用 — 僅在執行播放偵錯器時需要 |
| **pixel-art skill** | 16×16 精靈圖的設計知識：色相偏移色階、選擇性輪廓描繪、調色盤紀律。沒有它，精靈圖品質會明顯下降。 | 強烈建議 |

`scripts/bootstrap.sh` 會安裝除 Homebrew 本身以外的所有內容。執行一次即可。

## 安裝

### 如果你是 Claude Code 新手

請閱讀 [docs/SETUP.md](docs/SETUP.md) — 它會引導你在 30 分鐘內完成安裝 Claude Code，然後安裝此 skill。

### 如果你已有 Claude Code

在 Claude Code 中執行：

```
/plugin marketplace add meng-tsai/youtube-to-yoto
/plugin install youtube-to-yoto
```

重新啟動 Claude Code。然後讓它執行 bootstrap 以安裝管道相依套件：

```
> please run scripts/bootstrap.sh for the youtube-to-yoto skill
```

### 如果你使用 Cursor / Codex / OpenCode / 其他支援 skill 的 AI 代理

```bash
npx skills add meng-tsai/youtube-to-yoto
```

然後如上執行 bootstrap。

## 首次執行（建議：示範模式）

在 Claude Code 中，備好你的播放清單 URL：

```
> I want to put this YouTube playlist on my Yoto card:
> https://www.youtube.com/playlist?list=XXXXXXXXX
```

此 skill 會偵測到這是你的首次執行，並**建議只處理前 3 集**。請回答「是」。如果有任何問題（OAuth、卡片綁定、音訊格式），你只需花 5 分鐘就能發現，而不是 1.5 小時。

確認前 3 集在播放器上正常播放後，它會詢問是否繼續處理剩餘的集數。

## 完整管道參考

適用於想直接執行腳本、不透過 Claude 操作的使用者：

```bash
SKILL=~/.claude/skills/youtube-to-yoto

# Phase 1 — Download
bash $SKILL/scripts/download_playlist.sh \
  https://www.youtube.com/playlist?list=XXX  \
  /tmp/myplaylist                            \
  --first 3 --lang en

# Phase 2 — Transcribe
bash $SKILL/scripts/transcribe_all.sh \
  /tmp/myplaylist /tmp/myplaylist/transcripts

# Phase 3 — Subject extraction (via SubAgents in your Claude session)
# (Done conversationally — the skill walks you through it.)

# Phase 4 — Sprite generation (via SubAgents in your Claude session)
# (Cost confirm gate fires here.)

# Phase 5 — Upload
export YOTO_CLIENT_ID=<your client id>
python3 $SKILL/scripts/yoto_auth.py
python3 $SKILL/scripts/yoto_upload.py \
  --subjects /tmp/myplaylist/subjects.json \
  --sprites  /tmp/myplaylist/pixel_subjects \
  --mp3      /tmp/myplaylist \
  --title    "My playlist" \
  --go
```

完整 skill 規格請參閱 [skills/youtube-to-yoto/SKILL.md](skills/youtube-to-yoto/SKILL.md)，Yoto API 參考請見 [references/yoto-api.md](skills/youtube-to-yoto/references/yoto-api.md)，通過伺服器驗證但會導致播放器故障的已知問題清單請見 [references/pitfalls.md](skills/youtube-to-yoto/references/pitfalls.md)。

## OAuth

你需要從 https://dashboard.yoto.dev/ 取得 Yoto OAuth Client ID。此 skill 會在第一次使用時引導你完成申請。手動參考：[docs/OAUTH.md](docs/OAUTH.md)。

## 疑難排解

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) 涵蓋常見的失敗情況 — 播放器跳過曲目、OAuth 錯誤、yt-dlp 429 錯誤、配額問題。

## 硬性限制

- **每個播放清單 100 首曲目**（Yoto API 限制）。對於更大的收藏，請拆分至多張卡片。
- **僅支援 Mac**（v1）。強烈建議使用 Apple Silicon 以獲得 Whisper Metal 加速。
- **無 NFC 綁定 API** — 你必須在 Yoto app 開啟的情況下，實際將一張空白 MYO 卡片點擊播放器。

## 貢獻

歡迎提交 PR，特別是：

- `docs/SETUP.md`、`docs/OAUTH.md` 等的翻譯（目前只有 `README.md` 已翻譯）
- `docs/OAUTH.md` 的截圖
- 精靈圖範例庫的擴充

## 授權

[MIT](LICENSE)

## 致謝

- Yoto API 對應關係是從以下先前的專案逆向工程而來：`cjlm/yoto-playlist-creator`、`bperkinspdx/yoto-mcp-server`、`cdnninja/yoto_api`。
- 像素藝術設計指導來自 [omer-metin/skills-for-antigravity@pixel-art](https://github.com/omer-metin/skills-for-antigravity)。
- 以 [Claude Code](https://claude.ai/code) 建構。
