<!-- Translated from README.md @ 0cba4c6. Translations may lag behind English. PRs welcome. -->
[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · **한국어** · [Español](README.es.md) · [Français](README.fr.md)

# youtube-to-yoto

YouTube 재생목록을 [Yoto](https://yotoplay.com/) MYO("Make Your Own") 카드 재생목록으로 변환하며, 에피소드별 16×16 픽셀 아트 아이콘이 플레이어의 LED 매트릭스에 표시됩니다.

[Claude Code](https://claude.ai/code) 스킬 / 플러그인으로 제작되었습니다. v1은 Mac 전용입니다.

## 기능 소개

YouTube 재생목록 URL을 입력하면 다음 작업을 수행합니다:

1. 각 동영상의 오디오를 MP3로 다운로드합니다.
2. 각 에피소드의 처음 3분을 전사합니다 (로컬 Whisper 사용, 무료, API 호출 없음).
3. Claude SubAgent를 통해 에피소드당 그릴 수 있는 구체적인 명사 하나를 선택합니다 (예: `rhinoceros beetle`, `birthday cake`).
4. Claude SubAgent를 통해 고유한 명사마다 16×16 픽셀 아트 스프라이트를 디자인합니다.
5. 모든 것(오디오 + 스프라이트 + 재생목록 메타데이터)을 Yoto 계정에 업로드합니다.
6. 빈 MYO 카드를 플레이어에 탭하여 바인딩하도록 안내합니다.

약 100개 에피소드의 총 소요 시간: 약 1.5시간.

## 비용

> 설치 **전**에 읽어 주십시오.

이 스킬은 Claude SubAgent를 사용하여 픽셀 아트 아이콘을 디자인합니다. 비용은 **Claude 청구 방식**에 따라 다릅니다:

| 청구 방식 | 비용 |
|---|---|
| **Claude Pro / Max 구독** *(권장)* | 추가 비용 없음. SubAgent 실행은 기존 플랜 할당량에서 차감됩니다. 100개 에피소드 재생목록은 일반적으로 Max 세션 내에 들어맞습니다. |
| **종량제 API 키** | 고유 스프라이트당 약 $0.10–0.15 (Opus). 약 70개의 고유 주제가 있는 100개 에피소드 재생목록 ≈ **$7–$10**. |
| **무료 Claude 티어** | 할당량이 부족합니다 — 실행 전에 Pro로 업그레이드하십시오. |

스킬은 **항상 예상 비용을 사전에 공지**하며 SubAgent를 실행하기 전에 확인을 요청합니다. 부분 진행 상황은 캐시되어 재개할 수 있습니다.

자세한 내용: [docs/COSTS.md](docs/COSTS.md).

## 하드웨어 요구 사항

| 구성 요소 | 최소 사양 | 권장 사양 |
|---|---|---|
| macOS | 12 Monterey | 14 Sonoma+ |
| CPU | Intel Mac (3–5× 느림) | **Apple Silicon (M1+)** — whisper.cpp는 Metal GPU 가속을 사용하며, turbo는 M1에서 실시간의 약 15배 속도로 실행됩니다 |
| RAM | 8 GB | 16 GB (Whisper는 최대 2–3 GB 사용) |
| 여유 디스크 | 4 GB | 10 GB |
| 네트워크 | 안정적인 광대역 | 100개 에피소드에 약 800 MB 다운로드, Yoto에 약 800 MB 업로드 |
| 소요 시간 | — | 100개 에피소드 첫 실행 시 약 1.5시간 |

**Windows 및 Linux는 v1에서 지원되지 않습니다.**

## 디스크 공간

| 항목 | 크기 | 시점 |
|---|---|---|
| Whisper `large-v3-turbo` 모델 | **1.5 GB** | 1회, 모든 재생목록에서 공유 |
| brew 패키지 (yt-dlp, ffmpeg, whisper-cpp, node) | ~400 MB | 1회 |
| pip 패키지 (Pillow, requests, aiomqtt) | ~60 MB | 1회 |
| `pixel-art` 스킬 | ~2 MB | 1회 |
| 재생목록당 MP3 오디오 | 에피소드당 약 8 MB | 재생목록마다. 업로드 후 삭제 가능. 100개 에피소드 ≈ 800 MB. |
| 전사, 스프라이트, 캐시 | 총 5 MB 미만 | 무시할 수 있는 수준 |

**첫 실행 총합: 1회 약 2.5 GB + 재생목록당 약 1 GB.**

## 의존성 (및 필요한 이유)

필요한 모든 외부 도구와 그 용도:

| 의존성 | 필요한 이유 | 선택 사항? |
|---|---|---|
| **yt-dlp** | YouTube에서 오디오를 가져옵니다. 공식 YouTube 오디오 다운로드 API가 없습니다. | 필수 |
| **ffmpeg** | yt-dlp가 YouTube 스트림에서 MP3를 추출하기 위해 내부적으로 사용합니다. Whisper를 위한 3분 WAV 분할도 수행합니다. | 필수 |
| **whisper-cpp** + `ggml-large-v3-turbo` 모델 | Claude가 아이콘으로 그릴 구체적인 명사를 파악할 수 있도록 각 에피소드의 처음 3분을 전사합니다. "Episode 5: Friends"와 같은 YouTube 제목으로는 알 수 없습니다. | 선택 — YouTube 제목이 이미 충분히 구체적인 경우 스킬이 Phase 2를 건너뜁니다 |
| **node** | (1) yt-dlp가 YouTube의 봇 방지 챌린지를 해결하기 위해 Node를 JS 런타임으로 사용합니다. (2) `npx skills`가 `pixel-art` 스킬을 설치합니다. | 필수 |
| **Pillow** (pip) | 16×16 PNG 스프라이트 읽기/쓰기 | 필수 |
| **requests** (pip) | Yoto REST API용 HTTP 클라이언트 | 필수 |
| **aiomqtt** (pip) | `mqtt_log.py` 진단을 위한 비동기 MQTT 클라이언트 | 선택 — 재생 디버거를 실행하는 경우에만 필요 |
| **pixel-art 스킬** | 16×16 스프라이트 디자인 지식: 색조 변환 램프, 선택적 윤곽선, 팔레트 규칙. 이것 없이는 스프라이트 품질이 눈에 띄게 떨어집니다. | 강력 권장 |

`scripts/bootstrap.sh`는 Homebrew 자체를 제외한 모든 것을 설치합니다. 한 번 실행하십시오.

## 설치

### Claude Code를 처음 사용하는 경우

[docs/SETUP.md](docs/SETUP.md)를 읽어 주십시오 — Claude Code 설치부터 이 스킬 설치까지 30분 안에 안내해 드립니다.

### 이미 Claude Code를 사용 중인 경우

Claude Code 내에서:

```
/plugin marketplace add meng-tsai/youtube-to-yoto
/plugin install youtube-to-yoto
```

Claude Code를 재시작하십시오. 그런 다음 파이프라인 의존성을 설치하기 위해 bootstrap을 실행하도록 하십시오:

```
> please run scripts/bootstrap.sh for the youtube-to-yoto skill
```

### Cursor / Codex / OpenCode / 다른 스킬 호환 에이전트를 사용하는 경우

```bash
npx skills add meng-tsai/youtube-to-yoto
```

그런 다음 위와 같이 bootstrap을 실행하십시오.

## 첫 실행 (권장: 데모 모드)

Claude Code 내에서 재생목록 URL을 준비하고 다음을 입력하십시오:

```
> I want to put this YouTube playlist on my Yoto card:
> https://www.youtube.com/playlist?list=XXXXXXXXX
```

스킬이 첫 실행임을 감지하고 **처음 3개 에피소드만 실행할 것을 권장합니다**. 예라고 답하십시오. 문제가 있을 경우(OAuth, 카드 바인딩, 오디오 형식), 1.5시간이 아닌 5분 내에 발견할 수 있습니다.

플레이어에서 3개 에피소드가 올바르게 재생되는 것을 확인한 후, 나머지를 계속할지 여부를 물어볼 것입니다.

## 전체 파이프라인 참조

Claude를 통하지 않고 스크립트를 직접 실행하려는 사용자를 위한 참조입니다:

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

[skills/youtube-to-yoto/SKILL.md](skills/youtube-to-yoto/SKILL.md)에서 전체 스킬 사양을, [references/yoto-api.md](skills/youtube-to-yoto/references/yoto-api.md)에서 Yoto API 참조를, [references/pitfalls.md](skills/youtube-to-yoto/references/pitfalls.md)에서 서버 검증은 통과하지만 플레이어에서 오류를 발생시키는 버그 목록을 확인하십시오.

## OAuth

https://dashboard.yoto.dev/에서 Yoto OAuth Client ID가 필요합니다. 스킬이 처음 발급 과정을 안내해 드립니다. 수동 참조: [docs/OAUTH.md](docs/OAUTH.md).

## 문제 해결

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)에서 일반적인 오류 모드를 다룹니다 — 플레이어 트랙 건너뜀, OAuth 오류, yt-dlp 429 오류, 할당량 문제.

## 엄격한 제한

- **재생목록당 100개 트랙** (Yoto API 제한). 더 큰 컬렉션의 경우 카드에 분산하십시오.
- **Mac 전용** (v1). Whisper Metal 가속을 위해 Apple Silicon을 강력히 권장합니다.
- **NFC 바인딩 API 없음** — Yoto 앱이 열려 있는 상태에서 빈 MYO 카드를 플레이어에 직접 탭해야 합니다.

## 기여

PR을 환영합니다, 특히:

- `docs/SETUP.md`, `docs/OAUTH.md` 등의 번역 (현재 `README.md`만 번역되어 있습니다)
- `docs/OAUTH.md`용 스크린샷
- 샘플 스프라이트 라이브러리 확장

## 라이선스

[MIT](LICENSE)

## 감사의 말

- Yoto API 매핑은 다음 기존 프로젝트들을 역공학하여 작성되었습니다: `cjlm/yoto-playlist-creator`, `bperkinspdx/yoto-mcp-server`, `cdnninja/yoto_api`.
- 픽셀 아트 디자인 가이드는 [omer-metin/skills-for-antigravity@pixel-art](https://github.com/omer-metin/skills-for-antigravity)를 통해 제공됩니다.
- [Claude Code](https://claude.ai/code)로 제작되었습니다.
