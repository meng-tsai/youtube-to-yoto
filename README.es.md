<!-- Translated from README.md @ 0cba4c6. Translations may lag behind English. PRs welcome. -->
[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · **Español** · [Français](README.fr.md)

# youtube-to-yoto

Convierte cualquier lista de reproducción de YouTube en una lista de reproducción de tarjeta MYO ("Make Your Own") de [Yoto](https://yotoplay.com/) con íconos de pixel-art de 16×16 por episodio en la matriz LED del reproductor.

Construido como una habilidad / complemento de [Claude Code](https://claude.ai/code). Solo para Mac en la versión 1.

## Qué hace esto

Le proporcionan una URL de lista de reproducción de YouTube. El programa:

1. Descarga el audio de cada video como MP3.
2. Transcribe los primeros 3 minutos de cada uno (Whisper local, gratuito, sin llamada a la API).
3. Elige un sustantivo concreto y dibujable por episodio (p. ej., `rhinoceros beetle`, `birthday cake`) mediante SubAgentes de Claude.
4. Diseña un sprite de pixel-art de 16×16 por sustantivo único mediante SubAgentes de Claude.
5. Sube todo (audio + sprites + metadatos de la lista) a su cuenta de Yoto.
6. Les indica que toquen una tarjeta MYO en blanco sobre el reproductor para vincularla.

Tiempo total de reloj para ~100 episodios: ~1.5 horas.

## Costo

> Lean esto **antes** de instalar.

Esta habilidad usa SubAgentes de Claude para diseñar íconos de pixel-art. El costo depende de **cómo se factura Claude**:

| Facturación | Lo que les cuesta |
|---|---|
| **Suscripción Claude Pro / Max** *(recomendado)* | $0 adicional. Las ejecuciones de SubAgentes se descuentan de la cuota de su plan actual. Una lista de reproducción de 100 episodios suele caber en una sesión Max. |
| **Clave API de pago por uso** | ~$0.10–0.15 por sprite único (Opus). Una lista de 100 episodios con ~70 temas únicos ≈ **$7–$10**. |
| **Nivel gratuito de Claude** | Cuota insuficiente — actualicen a Pro antes de ejecutar. |

La habilidad **siempre anuncia el costo estimado al inicio** y solicita confirmación antes de lanzar los SubAgentes. El progreso parcial se guarda en caché y se puede reanudar.

Detalles: [docs/COSTS.md](docs/COSTS.md).

## Requisitos de hardware

| Componente | Mínimo | Recomendado |
|---|---|---|
| macOS | 12 Monterey | 14 Sonoma+ |
| CPU | Intel Mac (3–5× más lento) | **Apple Silicon (M1+)** — whisper.cpp usa aceleración GPU Metal; turbo corre ~15× en tiempo real en M1 |
| RAM | 8 GB | 16 GB (Whisper usa 2–3 GB en el pico) |
| Disco libre | 4 GB | 10 GB |
| Red | Banda ancha estable | Descarga ~800 MB para 100 episodios; sube ~800 MB a Yoto |
| Tiempo de reloj | — | ~1.5 horas para la primera ejecución de 100 episodios |

**Windows y Linux no están soportados en la versión 1.**

## Espacio en disco

| Elemento | Tamaño | Cuándo |
|---|---|---|
| Modelo Whisper `large-v3-turbo` | **1.5 GB** | Una sola vez, compartido entre todas las listas |
| Paquetes brew (yt-dlp, ffmpeg, whisper-cpp, node) | ~400 MB | Una sola vez |
| Paquetes pip (Pillow, requests, aiomqtt) | ~60 MB | Una sola vez |
| Habilidad `pixel-art` | ~2 MB | Una sola vez |
| Audio MP3 por lista | ~8 MB / episodio | Por lista. Se puede eliminar tras la subida. 100 episodios ≈ 800 MB. |
| Transcripciones, sprites, caché | < 5 MB en total | Insignificante |

**Total en la primera ejecución: ~2.5 GB una sola vez + ~1 GB por lista.**

## Dependencias (y por qué)

Cada herramienta externa necesaria y su función:

| Dependencia | Por qué la necesitamos | ¿Opcional? |
|---|---|---|
| **yt-dlp** | Descarga el audio de YouTube. No existe una API oficial de descarga de audio de YouTube. | Requerida |
| **ffmpeg** | yt-dlp la usa internamente para extraer MP3 de las transmisiones de YouTube. También recorta WAVs de 3 minutos para Whisper. | Requerida |
| **whisper-cpp** + modelo `ggml-large-v3-turbo` | Transcribe los primeros 3 minutos de cada episodio para que Claude sepa qué sustantivo concreto dibujar como ícono. Títulos de YouTube como "Episodio 5: Amigos" no lo indican. | Opcional — la habilidad omite la Fase 2 cuando los títulos de YouTube ya son suficientemente concretos para identificar el tema |
| **node** | (1) yt-dlp usa Node como entorno de ejecución JS para resolver el desafío anti-bot de YouTube. (2) `npx skills` instala la habilidad `pixel-art`. | Requerido |
| **Pillow** (pip) | Lee/escribe sprites PNG de 16×16 | Requerida |
| **requests** (pip) | Cliente HTTP para la API REST de Yoto | Requerida |
| **aiomqtt** (pip) | Cliente MQTT asíncrono para diagnósticos de `mqtt_log.py` | Opcional — solo si ejecutan el depurador de reproducción |
| **Habilidad pixel-art** | Conocimiento de diseño para sprites de 16×16: rampas con matiz desplazado, delineado selectivo, disciplina de paleta. Sin ella, la calidad de los sprites baja notablemente. | Muy recomendado |

`scripts/bootstrap.sh` instala todo excepto Homebrew en sí. Ejecútenlo una vez.

## Instalación

### Si son nuevos en Claude Code

Lean [docs/SETUP.md](docs/SETUP.md) — los guía paso a paso para instalar Claude Code y luego esta habilidad en 30 minutos.

### Si ya tienen Claude Code

Dentro de Claude Code:

```
/plugin marketplace add meng-tsai/youtube-to-yoto
/plugin install youtube-to-yoto
```

Reinicien Claude Code. Luego pídanle que ejecute el bootstrap para instalar las dependencias de la canalización:

```
> please run scripts/bootstrap.sh for the youtube-to-yoto skill
```

### Si usan Cursor / Codex / OpenCode / otro agente compatible con habilidades

```bash
npx skills add meng-tsai/youtube-to-yoto
```

Luego ejecuten el bootstrap como se indica arriba.

## Primera ejecución (recomendado: modo demo)

Dentro de Claude Code, con la URL de su lista de reproducción lista:

```
> I want to put this YouTube playlist on my Yoto card:
> https://www.youtube.com/playlist?list=XXXXXXXXX
```

La habilidad detecta que es la primera ejecución y **recomienda hacer solo los primeros 3 episodios**. Digan que sí. Si algo falla (OAuth, vinculación de tarjeta, formato de audio), lo detectarán en 5 minutos en lugar de 1.5 horas.

Después de confirmar que los 3 episodios se reproducen correctamente en el reproductor, les preguntará si desean continuar con el resto.

## Referencia completa de la canalización

Para usuarios que desean ejecutar los scripts directamente sin pasar por Claude:

```bash
SKILL=~/.claude/skills/youtube-to-yoto

# Fase 1 — Descarga
bash $SKILL/scripts/download_playlist.sh \
  https://www.youtube.com/playlist?list=XXX  \
  /tmp/myplaylist                            \
  --first 3 --lang en

# Fase 2 — Transcripción
bash $SKILL/scripts/transcribe_all.sh \
  /tmp/myplaylist /tmp/myplaylist/transcripts

# Fase 3 — Extracción de temas (mediante SubAgentes en su sesión de Claude)
# (Se realiza de forma conversacional — la habilidad los guía.)

# Fase 4 — Generación de sprites (mediante SubAgentes en su sesión de Claude)
# (Aquí se activa la puerta de confirmación de costo.)

# Fase 5 — Subida
export YOTO_CLIENT_ID=<your client id>
python3 $SKILL/scripts/yoto_auth.py
python3 $SKILL/scripts/yoto_upload.py \
  --subjects /tmp/myplaylist/subjects.json \
  --sprites  /tmp/myplaylist/pixel_subjects \
  --mp3      /tmp/myplaylist \
  --title    "My playlist" \
  --go
```

Consulten [skills/youtube-to-yoto/SKILL.md](skills/youtube-to-yoto/SKILL.md) para la especificación completa de la habilidad, [references/yoto-api.md](skills/youtube-to-yoto/references/yoto-api.md) para la referencia de la API de Yoto, y [references/pitfalls.md](skills/youtube-to-yoto/references/pitfalls.md) para la lista de errores que superan la validación del servidor pero rompen el reproductor.

## OAuth

Necesitan un ID de cliente OAuth de Yoto desde https://dashboard.yoto.dev/. La habilidad los guía para obtenerlo la primera vez. Referencia manual: [docs/OAUTH.md](docs/OAUTH.md).

## Solución de problemas

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) cubre los modos de fallo más comunes: el reproductor omite pistas, errores de OAuth, errores 429 de yt-dlp, problemas de cuota.

## Límites estrictos

- **100 pistas por lista de reproducción** (límite de la API de Yoto). Para colecciones más grandes, distribúyanlas entre varias tarjetas.
- **Solo Mac** (v1). Se recomienda enfáticamente Apple Silicon para la aceleración Metal de Whisper.
- **Sin API de vinculación NFC** — deben tocar físicamente una tarjeta MYO en blanco sobre el reproductor mientras la app de Yoto está abierta.

## Contribuciones

Se aceptan PRs, especialmente para:

- Traducciones de `docs/SETUP.md`, `docs/OAUTH.md`, etc. (actualmente solo `README.md` está traducido)
- Capturas de pantalla para `docs/OAUTH.md`
- Extensiones de la biblioteca de sprites de ejemplo

## Licencia

[MIT](LICENSE)

## Agradecimientos

- El mapeo de la API de Yoto fue obtenido mediante ingeniería inversa a partir de estos proyectos previos: `cjlm/yoto-playlist-creator`, `bperkinspdx/yoto-mcp-server`, `cdnninja/yoto_api`.
- Orientación de diseño de pixel-art a través de [omer-metin/skills-for-antigravity@pixel-art](https://github.com/omer-metin/skills-for-antigravity).
- Construido con [Claude Code](https://claude.ai/code).
