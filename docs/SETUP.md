# Setup — From Zero to First Run

This guide is for someone who has **never installed Claude Code**.
If you already have Claude Code working, skip to step 2.

Estimated time: 30 minutes.

## 1. Install Claude Code

Claude Code is Anthropic's official CLI for Claude. You'll run this
skill inside it.

### 1a. Install Node.js

Skip if you already have Node 18+ (`node --version`).

The easiest path on Mac is via Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install node
```

### 1b. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

### 1c. First launch and login

```bash
claude
```

The first time you run `claude`, it'll prompt you to sign in with
your Anthropic account. **You need either a Claude Pro / Max
subscription or a pay-as-you-go API key** — this skill will not work
on the free tier (not enough quota for sprite generation).

Confirm it's working:

```
> hello
```

You should see Claude reply. Quit with `Ctrl+D` or `/exit`.

## 2. Install the youtube-to-yoto plugin

Launch Claude Code again from any directory:

```bash
claude
```

Inside Claude Code, run:

```
/plugin marketplace add meng-tsai/youtube-to-yoto
/plugin install youtube-to-yoto
```

Quit and relaunch (`/exit` then `claude`) so the skill loads.

## 3. Install pipeline dependencies

Inside Claude Code:

```
> please run scripts/bootstrap.sh for the youtube-to-yoto skill
```

Claude will run the bootstrap script. It installs (idempotently):

- Homebrew packages: yt-dlp, ffmpeg, whisper-cpp, node
- pip packages: Pillow, requests, aiomqtt (optional)
- Whisper `large-v3-turbo` model (1.5 GB download, one-time)
- `pixel-art` skill (via `npx skills add`)

Total: ~2.5 GB of one-time downloads, ~10 minutes on a typical broadband connection.

## 4. Get a Yoto OAuth Client ID

You don't need to do this manually — the skill will walk you through it
the first time you ask it to upload. But if you want to prep ahead:

- Go to https://dashboard.yoto.dev/
- Sign in with your Yoto account email
- Create new app → name it anything → enable scope `user:content:manage`
- Copy the Client ID

Save it somewhere you can paste — you'll give it to Claude when prompted.

## 5. First run (demo mode — recommended)

Inside Claude Code, with your playlist URL ready:

```
> I want to put this YouTube playlist on my Yoto card:
> https://www.youtube.com/playlist?list=XXXXXXXXX
```

The skill will:

1. Detect this is your first run.
2. **Suggest doing the first 3 episodes only as a test** — please say yes.
3. Walk you through the OAuth setup (paste your Client ID when asked).
4. Download → transcribe → extract subjects → generate sprites → upload.
5. Tell you to insert a blank Yoto MYO card into your Player while the
   Yoto app is open, and choose the new playlist to bind it.

After you confirm the 3 episodes play correctly on the Player, the
skill will ask whether to continue with the rest. Say yes.

## 6. Troubleshooting

- **Player shows cloud icon and skips tracks rapidly** — almost
  always a payload-format bug. See `docs/TROUBLESHOOTING.md`.
- **`brew: command not found`** — Homebrew not installed. See step 1a.
- **`claude: command not found`** — Claude Code not installed or not
  on PATH. See step 1b.
- **OAuth Client ID gives "unauthorized_client"** — the `user:content:manage` scope wasn't enabled. Go back to dashboard.yoto.dev → app settings → check the box → save.

More in `docs/TROUBLESHOOTING.md`.

## What's next

- `docs/OAUTH.md` — the OAuth flow in detail (in case the conversational walkthrough breaks)
- `docs/COSTS.md` — how subagent usage affects your Claude quota / API bill
- `docs/TROUBLESHOOTING.md` — common failure modes and fixes
- `README.md` — feature reference, dep table, hardware requirements
