<!-- Translated from README.md @ 0cba4c6. Translations may lag behind English. PRs welcome. -->
[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · **Français**

# youtube-to-yoto

Transformez n'importe quelle liste de lecture YouTube en playlist de carte [Yoto](https://yotoplay.com/) MYO (« Make Your Own ») avec des icônes pixel art 16×16 par épisode affichées sur la matrice LED du Player.

Construit en tant que skill / plugin [Claude Code](https://claude.ai/code). Exclusivement macOS pour la v1.

## Ce que cela fait

Vous lui fournissez l'URL d'une liste de lecture YouTube. Il :

1. Télécharge l'audio de chaque vidéo en MP3.
2. Transcrit les 3 premières minutes de chacune (Whisper local, gratuit, sans appel API).
3. Choisit un nom commun concret et dessinable par épisode (par ex. `rhinoceros beetle`, `birthday cake`) via des Claude SubAgents.
4. Conçoit un sprite pixel art 16×16 par nom unique via des Claude SubAgents.
5. Envoie tout (audio + sprites + métadonnées de la playlist) vers votre compte Yoto.
6. Vous demande de poser une carte MYO vierge sur le Player pour l'associer.

Temps total d'exécution pour ~100 épisodes : ~1,5 heure.

## Coût

> Lisez ceci **avant** d'installer.

Cette skill utilise des Claude SubAgents pour concevoir des icônes pixel art. Le coût dépend de **la façon dont vous êtes facturé pour Claude** :

| Facturation | Ce que cela vous coûte |
|---|---|
| **Abonnement Claude Pro / Max** *(recommandé)* | 0 $ supplémentaire. Les exécutions SubAgent sont déduites du quota de votre abonnement actuel. Une playlist de 100 épisodes tient généralement dans une session Max. |
| **Clé API à la consommation** | ~0,10–0,15 $ par sprite unique (Opus). Une playlist de 100 épisodes avec ~70 sujets uniques ≈ **7–10 $**. |
| **Niveau gratuit Claude** | Quota insuffisant — passez à Pro avant de lancer. |

La skill **annonce toujours le coût estimé à l'avance** et vous demande de confirmer avant de déployer les SubAgents. La progression partielle est mise en cache et peut être reprise.

Détails : [docs/COSTS.md](docs/COSTS.md).

## Configuration matérielle requise

| Composant | Minimum | Recommandé |
|---|---|---|
| macOS | 12 Monterey | 14 Sonoma+ |
| CPU | Mac Intel (3–5× plus lent) | **Apple Silicon (M1+)** — whisper.cpp utilise l'accélération GPU Metal ; turbo tourne à ~15× la vitesse réelle sur M1 |
| RAM | 8 Go | 16 Go (Whisper utilise 2–3 Go au pic) |
| Espace disque libre | 4 Go | 10 Go |
| Réseau | Haut débit stable | Télécharge ~800 Mo pour 100 épisodes ; envoie ~800 Mo vers Yoto |
| Temps d'exécution | — | ~1,5 heure pour une première exécution de 100 épisodes |

**Windows et Linux ne sont pas pris en charge dans la v1.**

## Espace disque

| Élément | Taille | Quand |
|---|---|---|
| Modèle Whisper `large-v3-turbo` | **1,5 Go** | Une fois, partagé entre toutes les playlists |
| Paquets brew (yt-dlp, ffmpeg, whisper-cpp, node) | ~400 Mo | Une fois |
| Paquets pip (Pillow, requests, aiomqtt) | ~60 Mo | Une fois |
| Skill `pixel-art` | ~2 Mo | Une fois |
| Audio MP3 par playlist | ~8 Mo / épisode | Par playlist. Peut être supprimé après envoi. 100 épisodes ≈ 800 Mo. |
| Transcriptions, sprites, cache | < 5 Mo au total | Négligeable |

**Total première exécution : ~2,5 Go en une fois + ~1 Go par playlist.**

## Dépendances (et pourquoi)

Chaque outil externe dont nous avons besoin, et à quoi il sert :

| Dépendance | Pourquoi nous en avons besoin | Optionnel ? |
|---|---|---|
| **yt-dlp** | Récupère l'audio depuis YouTube. Il n'existe pas d'API officielle de téléchargement audio YouTube. | Requis |
| **ffmpeg** | yt-dlp l'utilise en interne pour extraire le MP3 des flux YouTube. Sert aussi à découper des WAV de 3 min pour Whisper. | Requis |
| **whisper-cpp** + modèle `ggml-large-v3-turbo` | Transcrit les 3 premières minutes de chaque épisode pour que Claude sache quel nom concret dessiner comme icône. Les titres YouTube tels que « Episode 5: Friends » ne nous renseignent pas. | Optionnel — la skill saute la Phase 2 lorsque les titres YouTube sont déjà suffisamment concrets pour identifier le sujet |
| **node** | (1) yt-dlp utilise Node comme runtime JS pour résoudre le défi anti-bot de YouTube. (2) `npx skills` installe la skill `pixel-art`. | Requis |
| **Pillow** (pip) | Lit/écrit des sprites PNG 16×16 | Requis |
| **requests** (pip) | Client HTTP pour l'API REST Yoto | Requis |
| **aiomqtt** (pip) | Client MQTT asynchrone pour les diagnostics `mqtt_log.py` | Optionnel — uniquement si vous exécutez le débogueur de lecture |
| **Skill pixel-art** | Savoir-faire en conception de sprites 16×16 : rampes de teintes décalées, contours sélectifs, discipline de palette. Sans elle, la qualité des sprites diminue sensiblement. | Fortement recommandé |

`scripts/bootstrap.sh` installe tout sauf Homebrew lui-même. Lancez-le une fois.

## Installation

### Si vous débutez avec Claude Code

Lisez [docs/SETUP.md](docs/SETUP.md) — ce guide vous explique comment installer Claude Code, puis cette skill, en 30 minutes.

### Si vous avez déjà Claude Code

Dans Claude Code :

```
/plugin marketplace add meng-tsai/youtube-to-yoto
/plugin install youtube-to-yoto
```

Redémarrez Claude Code. Demandez-lui ensuite d'exécuter le bootstrap pour installer les dépendances du pipeline :

```
> please run scripts/bootstrap.sh for the youtube-to-yoto skill
```

### Si vous utilisez Cursor / Codex / OpenCode / un autre agent compatible avec les skills

```bash
npx skills add meng-tsai/youtube-to-yoto
```

Puis exécutez le bootstrap comme indiqué ci-dessus.

## Première exécution (recommandé : mode démo)

Dans Claude Code, avec l'URL de votre playlist prête :

```
> I want to put this YouTube playlist on my Yoto card:
> https://www.youtube.com/playlist?list=XXXXXXXXX
```

La skill détecte qu'il s'agit de votre première exécution et **recommande de ne traiter que les 3 premiers épisodes**. Acceptez. En cas de problème (OAuth, association de carte, format audio), vous le détecterez en 5 minutes plutôt qu'en 1,5 heure.

Après avoir confirmé que les 3 épisodes se lisent correctement sur le Player, la skill vous demandera si vous souhaitez continuer avec le reste.

## Référence complète du pipeline

Pour les utilisateurs qui souhaitent exécuter les scripts directement sans passer par Claude :

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

Consultez [skills/youtube-to-yoto/SKILL.md](skills/youtube-to-yoto/SKILL.md) pour la spécification complète de la skill, [references/yoto-api.md](skills/youtube-to-yoto/references/yoto-api.md) pour la référence de l'API Yoto, et [references/pitfalls.md](skills/youtube-to-yoto/references/pitfalls.md) pour la liste des bugs qui passent la validation serveur mais bloquent le Player.

## OAuth

Vous avez besoin d'un identifiant client OAuth Yoto depuis https://dashboard.yoto.dev/. La skill vous guide pour en obtenir un la première fois. Référence manuelle : [docs/OAUTH.md](docs/OAUTH.md).

## Dépannage

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) couvre les modes de défaillance courants — le Player qui saute des pistes, les erreurs OAuth, les erreurs 429 de yt-dlp, les problèmes de quota.

## Limites strictes

- **100 pistes par playlist** (limite de l'API Yoto). Pour les collections plus grandes, répartissez sur plusieurs cartes.
- **Mac uniquement** (v1). Apple Silicon fortement recommandé pour l'accélération Metal de Whisper.
- **Pas d'API de liaison NFC** — vous devez physiquement poser une carte MYO vierge sur le Player pendant que l'application Yoto est ouverte.

## Contribuer

Les PR sont les bienvenues, notamment pour :

- Les traductions de `docs/SETUP.md`, `docs/OAUTH.md`, etc. (seul `README.md` est actuellement traduit)
- Les captures d'écran pour `docs/OAUTH.md`
- Les extensions de bibliothèques de sprites

## Licence

[MIT](LICENSE)

## Remerciements

- Le mappage de l'API Yoto a été rétro-ingénié à partir de ces projets antérieurs : `cjlm/yoto-playlist-creator`, `bperkinspdx/yoto-mcp-server`, `cdnninja/yoto_api`.
- Conseils de conception pixel art via [omer-metin/skills-for-antigravity@pixel-art](https://github.com/omer-metin/skills-for-antigravity).
- Construit avec [Claude Code](https://claude.ai/code).
