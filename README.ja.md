<!-- Translated from README.md @ 0cba4c6. Translations may lag behind English. PRs welcome. -->
[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · **日本語** · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md)

# youtube-to-yoto

YouTube のプレイリストを [Yoto](https://yotoplay.com/) の MYO（"Make Your Own"）カードプレイリストに変換し、エピソードごとに 16×16 ピクセルアートアイコンをプレーヤーの LED マトリクスに表示します。

[Claude Code](https://claude.ai/code) のスキル・プラグインとして構築されています。v1 は Mac 専用です。

## このツールの機能

YouTube プレイリストの URL を渡すと、次の処理を行います：

1. 各動画の音声を MP3 としてダウンロードします。
2. 各エピソードの冒頭 3 分間をトランスクライブします（ローカルの Whisper を使用、無料、API 呼び出しなし）。
3. Claude SubAgents を使用して、エピソードごとに描画可能な具体的な名詞（例：`rhinoceros beetle`、`birthday cake`）を 1 つ選択します。
4. Claude SubAgents を使用して、ユニークな名詞ごとに 16×16 ピクセルアートスプライトをデザインします。
5. すべてのコンテンツ（音声・スプライト・プレイリストのメタデータ）を Yoto アカウントにアップロードします。
6. 空の MYO カードをプレーヤーにタップしてバインドするよう案内します。

約 100 エピソードの場合の所要時間：約 1.5 時間。

## コスト

> インストール**前**に必ずお読みください。

このスキルは Claude SubAgents を使用してピクセルアートアイコンをデザインします。コストは **Claude の課金方式**によって異なります：

| 課金方式 | 費用 |
|---|---|
| **Claude Pro / Max サブスクリプション**（推奨） | 追加費用なし。SubAgent の実行は既存プランのクォータから差し引かれます。100 エピソードのプレイリストは通常 Max セッション内に収まります。 |
| **従量課金 API キー** | スプライト 1 枚あたり約 $0.10〜$0.15（Opus）。約 70 個のユニークな題材を持つ 100 エピソードのプレイリスト ≈ **$7〜$10**。 |
| **Claude 無料プラン** | クォータが不足しています。実行前に Pro にアップグレードしてください。 |

このスキルは**常に推定コストを事前に通知**し、SubAgents をファンアウトする前に確認を求めます。途中経過はキャッシュされ、再開可能です。

詳細：[docs/COSTS.md](docs/COSTS.md)。

## ハードウェア要件

| コンポーネント | 最小要件 | 推奨 |
|---|---|---|
| macOS | 12 Monterey | 14 Sonoma 以上 |
| CPU | Intel Mac（3〜5 倍遅くなります） | **Apple Silicon（M1 以上）** — whisper.cpp が Metal GPU アクセラレーションを使用。M1 では turbo モードが約 15 倍のリアルタイム速度で動作します。 |
| RAM | 8 GB | 16 GB（Whisper はピーク時に 2〜3 GB 使用） |
| 空きディスク容量 | 4 GB | 10 GB |
| ネットワーク | 安定したブロードバンド | 100 エピソードで約 800 MB をダウンロード、Yoto に約 800 MB をアップロード |
| 所要時間 | — | 100 エピソードの初回実行で約 1.5 時間 |

**Windows および Linux は v1 では非対応です。**

## ディスク容量

| 項目 | サイズ | タイミング |
|---|---|---|
| Whisper `large-v3-turbo` モデル | **1.5 GB** | 初回のみ、全プレイリストで共有 |
| brew パッケージ（yt-dlp、ffmpeg、whisper-cpp、node） | 約 400 MB | 初回のみ |
| pip パッケージ（Pillow、requests、aiomqtt） | 約 60 MB | 初回のみ |
| `pixel-art` スキル | 約 2 MB | 初回のみ |
| プレイリストごとの MP3 音声 | 約 8 MB / エピソード | プレイリストごと。アップロード後は削除可能。100 エピソード ≈ 800 MB。 |
| トランスクリプト、スプライト、キャッシュ | 合計 5 MB 未満 | 無視できる程度 |

**初回合計：約 2.5 GB（初回のみ）+ プレイリストごとに約 1 GB。**

## 依存関係（とその理由）

必要な外部ツールとその用途：

| 依存関係 | 用途 | 省略可能？ |
|---|---|---|
| **yt-dlp** | YouTube から音声を取得します。公式の YouTube 音声ダウンロード API は存在しません。 | 必須 |
| **ffmpeg** | yt-dlp が内部で使用し、YouTube のストリームから MP3 を抽出します。また Whisper 用に 3 分間の WAV をスライスします。 | 必須 |
| **whisper-cpp** + `ggml-large-v3-turbo` モデル | 各エピソードの冒頭 3 分間をトランスクライブし、Claude がアイコンとして描くべき具体的な名詞を識別します。「Episode 5: Friends」のような YouTube タイトルだけでは判断できません。 | 省略可能 — YouTube タイトルがすでに題材を識別できるほど具体的な場合、スキルはフェーズ 2 をスキップします。 |
| **node** | （1）yt-dlp が YouTube のボット対策チャレンジを解決する JS ランタイムとして使用。（2）`npx skills` が `pixel-art` スキルをインストール。 | 必須 |
| **Pillow**（pip） | 16×16 PNG スプライトの読み書き | 必須 |
| **requests**（pip） | Yoto REST API の HTTP クライアント | 必須 |
| **aiomqtt**（pip） | `mqtt_log.py` 診断用の非同期 MQTT クライアント | 省略可能 — 再生デバッガーを使用する場合のみ |
| **pixel-art スキル** | 16×16 スプライトのデザイン知識：色相シフトランプ、選択的アウトライン、パレット管理。これがないとスプライトの品質が著しく低下します。 | 強く推奨 |

`scripts/bootstrap.sh` は Homebrew 本体を除くすべてをインストールします。一度だけ実行してください。

## インストール

### Claude Code を初めて使う方へ

[docs/SETUP.md](docs/SETUP.md) をお読みください。Claude Code のインストールからこのスキルのインストールまで、30 分で完了する手順を説明しています。

### すでに Claude Code をお持ちの方へ

Claude Code 内で次のコマンドを実行してください：

```
/plugin marketplace add meng-tsai/youtube-to-yoto
/plugin install youtube-to-yoto
```

Claude Code を再起動し、パイプラインの依存関係をインストールするためにブートストラップを実行させてください：

```
> please run scripts/bootstrap.sh for the youtube-to-yoto skill
```

### Cursor / Codex / OpenCode / その他のスキル対応エージェントを使用している方へ

```bash
npx skills add meng-tsai/youtube-to-yoto
```

その後、上記と同様にブートストラップを実行してください。

## 初回実行（推奨：デモモード）

Claude Code 内で、プレイリスト URL を用意した状態で次のように入力します：

```
> I want to put this YouTube playlist on my Yoto card:
> https://www.youtube.com/playlist?list=XXXXXXXXX
```

スキルは初回実行を検出し、**最初の 3 エピソードのみで試すことを推奨**します。承諾してください。何か問題（OAuth、カードのバインド、音声フォーマット）があれば、1.5 時間ではなく 5 分で発見できます。

3 エピソードがプレーヤーで正常に再生されることを確認したら、残りのエピソードを続行するかどうか確認します。

## フルパイプラインリファレンス

Claude を経由せずスクリプトを直接操作したいユーザー向け：

```bash
SKILL=~/.claude/skills/youtube-to-yoto

# フェーズ 1 — ダウンロード
bash $SKILL/scripts/download_playlist.sh \
  https://www.youtube.com/playlist?list=XXX  \
  /tmp/myplaylist                            \
  --first 3 --lang en

# フェーズ 2 — トランスクリプション
bash $SKILL/scripts/transcribe_all.sh \
  /tmp/myplaylist /tmp/myplaylist/transcripts

# フェーズ 3 — 題材抽出（Claude セッション内の SubAgents 経由）
# （会話形式で実行 — スキルが手順を案内します。）

# フェーズ 4 — スプライト生成（Claude セッション内の SubAgents 経由）
# （ここでコスト確認ゲートが発動します。）

# フェーズ 5 — アップロード
export YOTO_CLIENT_ID=<your client id>
python3 $SKILL/scripts/yoto_auth.py
python3 $SKILL/scripts/yoto_upload.py \
  --subjects /tmp/myplaylist/subjects.json \
  --sprites  /tmp/myplaylist/pixel_subjects \
  --mp3      /tmp/myplaylist \
  --title    "My playlist" \
  --go
```

スキル仕様の全文は [skills/youtube-to-yoto/SKILL.md](skills/youtube-to-yoto/SKILL.md)、Yoto API リファレンスは [references/yoto-api.md](skills/youtube-to-yoto/references/yoto-api.md)、サーバーのバリデーションは通過するがプレーヤーで動作しないバグの一覧は [references/pitfalls.md](skills/youtube-to-yoto/references/pitfalls.md) をご参照ください。

## OAuth

https://dashboard.yoto.dev/ から Yoto OAuth クライアント ID を取得する必要があります。スキルが初回利用時に手順を案内します。手動での参照：[docs/OAUTH.md](docs/OAUTH.md)。

## トラブルシューティング

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) では、一般的な障害モード（プレーヤーのトラックスキップ、OAuth エラー、yt-dlp の 429 エラー、クォータの問題）について説明しています。

## 制限事項

- **プレイリストあたり 100 トラック**（Yoto API の制限）。大規模なコレクションはカードを分けてください。
- **Mac 専用**（v1）。Whisper の Metal アクセラレーションのために Apple Silicon を強く推奨します。
- **NFC バインド API なし** — Yoto アプリを開いた状態でプレーヤーに空の MYO カードを物理的にタップする必要があります。

## コントリビューション

プルリクエストを歓迎します。特に以下を求めています：

- `docs/SETUP.md`、`docs/OAUTH.md` などの翻訳（現在翻訳済みなのは `README.md` のみです）
- `docs/OAUTH.md` 用のスクリーンショット
- サンプルスプライトライブラリの拡張

## ライセンス

[MIT](LICENSE)

## 謝辞

- Yoto API のマッピングは以下のプロジェクトをリバースエンジニアリングしました：`cjlm/yoto-playlist-creator`、`bperkinspdx/yoto-mcp-server`、`cdnninja/yoto_api`。
- ピクセルアートデザインガイダンスは [omer-metin/skills-for-antigravity@pixel-art](https://github.com/omer-metin/skills-for-antigravity) を参照しています。
- [Claude Code](https://claude.ai/code) を使用して構築されました。
