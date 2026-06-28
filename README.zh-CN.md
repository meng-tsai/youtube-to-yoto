<!-- Translated from README.md @ 0cba4c6. Translations may lag behind English. PRs welcome. -->
[English](README.md) · [繁體中文](README.zh-TW.md) · **简体中文** · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md)

# youtube-to-yoto

将任意 YouTube 播放列表转换为 [Yoto](https://yotoplay.com/) MYO（"Make Your Own"）卡片播放列表，并为每集生成 16×16 像素艺术图标，显示在播放器的 LED 矩阵上。

作为 [Claude Code](https://claude.ai/code) 技能 / 插件构建。v1 仅支持 Mac。

## 功能说明

你只需提供一个 YouTube 播放列表 URL，它会：

1. 将每个视频的音频下载为 MP3。
2. 转录每集的前 3 分钟（本地 Whisper，免费，无需 API 调用）。
3. 通过 Claude SubAgents 为每集挑选一个可绘制的具体名词（例如 `rhinoceros beetle`、`birthday cake`）。
4. 通过 Claude SubAgents 为每个唯一名词设计一个 16×16 像素艺术精灵图。
5. 将所有内容（音频 + 精灵图 + 播放列表元数据）上传到你的 Yoto 账户。
6. 提示你将一张空白 MYO 卡片贴靠播放器以绑定。

约 100 集的总用时：约 1.5 小时。

## 费用

> 安装前请**先阅读本节**。

此技能使用 Claude SubAgents 设计像素艺术图标。费用取决于**你的 Claude 计费方式**：

| 计费方式 | 你的费用 |
|---|---|
| **Claude Pro / Max 订阅** *（推荐）* | $0 额外费用。SubAgent 运行消耗现有套餐配额。100 集播放列表通常在 Max 单次会话内完成。 |
| **按量付费 API 密钥** | 每个唯一精灵图约 $0.10–0.15（Opus）。100 集播放列表含约 70 个唯一主题 ≈ **$7–$10**。 |
| **Claude 免费层** | 配额不足——运行前请升级到 Pro。 |

此技能**始终会在开始前公告预估费用**，并在分发 SubAgents 前请求你确认。已完成的进度会被缓存，可随时续跑。

详情：[docs/COSTS.md](docs/COSTS.md)。

## 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|---|---|---|
| macOS | 12 Monterey | 14 Sonoma+ |
| CPU | Intel Mac（慢 3–5 倍）| **Apple Silicon（M1+）**——whisper.cpp 使用 Metal GPU 加速；turbo 在 M1 上可达约 15 倍实时速度 |
| RAM | 8 GB | 16 GB（Whisper 峰值占用 2–3 GB）|
| 可用磁盘 | 4 GB | 10 GB |
| 网络 | 稳定宽带 | 100 集下载约 800 MB；上传至 Yoto 约 800 MB |
| 总用时 | — | 100 集首次运行约 1.5 小时 |

**v1 不支持 Windows 和 Linux。**

## 磁盘空间

| 项目 | 大小 | 时机 |
|---|---|---|
| Whisper `large-v3-turbo` 模型 | **1.5 GB** | 一次性，所有播放列表共用 |
| brew 套件（yt-dlp、ffmpeg、whisper-cpp、node）| 约 400 MB | 一次性 |
| pip 套件（Pillow、requests、aiomqtt）| 约 60 MB | 一次性 |
| `pixel-art` 技能 | 约 2 MB | 一次性 |
| 每个播放列表的 MP3 音频 | 约 8 MB / 集 | 每个播放列表。上传后可删除。100 集 ≈ 800 MB。|
| 转录文本、精灵图、缓存 | 合计 < 5 MB | 可忽略不计 |

**首次运行总计：约 2.5 GB 一次性 + 约 1 GB / 播放列表。**

## 依赖项（及其用途）

所需的每个外部工具及其用途：

| 依赖项 | 用途 | 可选？ |
|---|---|---|
| **yt-dlp** | 从 YouTube 拉取音频。官方没有 YouTube 音频下载 API。| 必需 |
| **ffmpeg** | yt-dlp 内部使用它从 YouTube 流中提取 MP3，同时用于为 Whisper 切割 3 分钟 WAV 片段。| 必需 |
| **whisper-cpp** + `ggml-large-v3-turbo` 模型 | 转录每集前 3 分钟，让 Claude 知道该画哪个具体名词作为图标。像"Episode 5: Friends"这样的 YouTube 标题并不能告诉我们主题。| 可选——当 YouTube 标题已经足够具体、可直接识别主题时，技能会跳过第 2 阶段 |
| **node** | (1) yt-dlp 使用 Node 作为 JS 运行时来解决 YouTube 的反爬虫挑战。(2) `npx skills` 用于安装 `pixel-art` 技能。| 必需 |
| **Pillow**（pip）| 读写 16×16 PNG 精灵图 | 必需 |
| **requests**（pip）| Yoto REST API 的 HTTP 客户端 | 必需 |
| **aiomqtt**（pip）| `mqtt_log.py` 诊断用的异步 MQTT 客户端 | 可选——仅在使用播放调试器时需要 |
| **pixel-art 技能** | 16×16 精灵图的设计知识：色相偏移渐变、选择性描边、调色板约束。缺少它，精灵图质量会明显下降。| 强烈推荐 |

`scripts/bootstrap.sh` 会安装除 Homebrew 本身以外的所有内容。运行一次即可。

## 安装

### 如果你是 Claude Code 新用户

请阅读 [docs/SETUP.md](docs/SETUP.md)——它会引导你在 30 分钟内完成 Claude Code 及本技能的安装。

### 如果你已有 Claude Code

在 Claude Code 中执行：

```
/plugin marketplace add meng-tsai/youtube-to-yoto
/plugin install youtube-to-yoto
```

重启 Claude Code。然后让它运行 bootstrap 以安装流水线依赖：

```
> please run scripts/bootstrap.sh for the youtube-to-yoto skill
```

### 如果你使用 Cursor / Codex / OpenCode / 其他兼容技能的 Agent

```bash
npx skills add meng-tsai/youtube-to-yoto
```

然后按上述方式运行 bootstrap。

## 首次运行（推荐：演示模式）

在 Claude Code 中，准备好播放列表 URL：

```
> I want to put this YouTube playlist on my Yoto card:
> https://www.youtube.com/playlist?list=XXXXXXXXX
```

技能会检测到你是首次运行，并**建议仅处理前 3 集**。选择是。如果有任何问题（OAuth、卡片绑定、音频格式），你能在 5 分钟内发现，而不必等待 1.5 小时。

确认前 3 集在播放器上正常播放后，它会询问是否继续处理剩余内容。

## 完整流水线参考

适合希望不经过 Claude 直接驱动脚本的用户：

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

请参阅 [skills/youtube-to-yoto/SKILL.md](skills/youtube-to-yoto/SKILL.md) 获取完整技能规格，[references/yoto-api.md](skills/youtube-to-yoto/references/yoto-api.md) 获取 Yoto API 参考文档，[references/pitfalls.md](skills/youtube-to-yoto/references/pitfalls.md) 获取通过服务器验证但会导致播放器异常的已知 bug 列表。

## OAuth

你需要从 https://dashboard.yoto.dev/ 获取 Yoto OAuth 客户端 ID。技能会在首次运行时引导你完成获取流程。手动参考：[docs/OAUTH.md](docs/OAUTH.md)。

## 故障排除

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) 涵盖了常见故障模式——播放器跳曲、OAuth 错误、yt-dlp 429 限速、配额问题。

## 硬性限制

- **每个播放列表最多 100 首曲目**（Yoto API 限制）。对于更大的合集，请分拆到多张卡片上。
- **仅支持 Mac**（v1）。强烈推荐 Apple Silicon 以获得 Whisper Metal 加速。
- **无 NFC 绑定 API**——你必须在 Yoto 应用打开时，将一张空白 MYO 卡片实体贴靠播放器。

## 贡献

欢迎提交 PR，尤其是：

- `docs/SETUP.md`、`docs/OAUTH.md` 等文档的翻译（目前仅翻译了 `README.md`）
- `docs/OAUTH.md` 的截图
- 示例精灵图库扩展

## 许可证

[MIT](LICENSE)

## 致谢

- Yoto API 映射通过逆向工程以下项目得出：`cjlm/yoto-playlist-creator`、`bperkinspdx/yoto-mcp-server`、`cdnninja/yoto_api`。
- 像素艺术设计指导来自 [omer-metin/skills-for-antigravity@pixel-art](https://github.com/omer-metin/skills-for-antigravity)。
- 使用 [Claude Code](https://claude.ai/code) 构建。
