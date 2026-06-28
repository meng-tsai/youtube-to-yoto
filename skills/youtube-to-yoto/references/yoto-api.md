# Yoto API reference

Exact endpoints, OAuth flow, and the playlist payload schema that the Yoto Player firmware actually accepts. Schema verified against the Yoto Zod schema at https://yoto.dev/myo/how-playlists-work/, the official end-to-end tutorial at https://yoto.dev/myo/uploading-to-cards/, and a production write-through to a real Player.

## Base URLs

- Auth: `https://login.yotoplay.com`
- API: `https://api.yotoplay.com`
- Developer dashboard: `https://dashboard.yoto.dev/`
- MQTT broker (AWS IoT): `aqrphjqbp3u2z-ats.iot.eu-west-2.amazonaws.com:443` (transport: `websockets`)

## OAuth — Device Code Flow

### 1. Get a device code
```
POST /oauth/device/code  (on login.yotoplay.com)
Content-Type: application/x-www-form-urlencoded

client_id=YOUR_CLIENT_ID
&scope=user:content:manage family:devices:view family:library:view
&audience=https://api.yotoplay.com
```

Response: `{user_code, verification_uri_complete, device_code, interval, expires_in}`. Show the user `verification_uri_complete` (or the URI + code separately); they approve in browser.

### 2. Poll for the token
```
POST /oauth/token  (on login.yotoplay.com)
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:device_code
&device_code={device_code}
&client_id=YOUR_CLIENT_ID
&audience=https://api.yotoplay.com
```

While pending you receive `{"error":"authorization_pending"}`. On approval:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "v1.M...",     // present only if offline_access scope is enabled in dashboard
  "expires_in": 86400,
  "token_type": "Bearer",
  "scope": "user:content:manage family:devices:view family:library:view"
}
```

### Scopes
| Scope | Required for |
|---|---|
| `user:content:manage` | Upload icons, upload audio, POST /content (this is the only scope needed for the upload pipeline) |
| `user:content:view` | GET /content/{cardId} — only needed if you want to read existing card content back |
| `family:devices:view` | GET /device-v2/devices/mine, MQTT subscribe (needed for diagnostics, not for upload) |
| `family:library:view` | GET /content/{cardId} on family-shared cards |
| `offline_access` | Receive a refresh_token (enable in dashboard if you want long-lived sessions) |

Multiple scopes are space-separated in the device code request.

### 3. Refresh (if you have a refresh_token)
```
POST /oauth/token
grant_type=refresh_token&client_id=...&refresh_token=...
```

## Audio upload

### 1. Get an upload URL
```
GET /media/transcode/audio/uploadUrl?sha256={sha256_of_mp3}&filename={mp3_name}
Authorization: Bearer {access_token}
```

Response:
```json
{
  "upload": {
    "uploadId": "...",
    "uploadUrl": "https://yoto-media-api-prod-uploads.s3.eu-west-2.amazonaws.com/..."
  }
}
```

If `uploadUrl` is `null`: Yoto has deduplicated this file by SHA256; skip the PUT and go straight to polling.

### 2. PUT the audio bytes
```
PUT {uploadUrl}
Content-Type: audio/mpeg

<binary MP3 bytes>
```

### 3. Poll for the transcoded result
```
GET /media/upload/{uploadId}/transcoded?loudnorm=false
Authorization: Bearer {access_token}
```

Yoto transcodes ANY input format to **Opus codec in Ogg container** at ~96 kbps. While in progress: `{"transcode":{"progress":{"phase":"..."}}}`. When complete:
```json
{
  "transcode": {
    "transcodedSha256": "w6nysWdU3ttMeTL2pU9GtzG3BFvaDk0b11iwqUhY0FE",
    "transcodedInfo": {
      "duration": 533,            // SECONDS
      "fileSize": 5552610,        // BYTES
      "codec": "opus",
      "format": "opus",
      "sampleRate": 48000,
      "bitrate": 83,
      "channels": "stereo"
    },
    "progress": {"phase": "complete", "percent": 100}
  }
}
```

Save `transcodedSha256`, `duration`, `fileSize`. Poll every 2-3s; transcoding takes ~5-30s per typical episode.

## Icon upload

```
POST /media/displayIcons/user/me/upload?autoConvert=true&filename={png_name}
Authorization: Bearer {access_token}
Content-Type: image/png

<raw PNG bytes>      ← NOT multipart form-data
```

`autoConvert=true` lets Yoto resize anything to 16×16 server-side. Response:
```json
{
  "displayIcon": {
    "mediaId": "XBkuY6DBFn5iRfFS6nV6CTWaCrEvBOOX8nzV9Y64h8I",
    "url": "https://media-secure-v2.api.yotoplay.com/icons/...",
    "new": true
  }
}
```

Save `mediaId` — referenced in chapter payloads as `yoto:#{mediaId}`.

## Playlist content (create or update)

```
POST /content
Authorization: Bearer {access_token}
Content-Type: application/json
```

Body:
```json
{
  "cardId": "ci8iF",
  "title": "巧虎全集",
  "metadata": {
    "description": "Auto-uploaded via API",
    "media": {
      "duration": 25028,
      "fileSize": 265299898,
      "readableFileSize": 253.0
    },
    "cover": {
      "imageL": "https://cdn.yoto.io/myo-cover/star_grapefruit.gif"
    }
  },
  "content": {
    "activity": "yoto_Player",
    "version": "1",
    "config": {
      "onlineOnly": false
    },
    "chapters": [
      {
        "key": "001",
        "title": "Episode title",
        "overlayLabel": "1",
        "tracks": [{
          "key": "001",
          "title": "Episode title",
          "overlayLabel": "1",
          "trackUrl": "yoto:#<transcodedSha256>",
          "duration": 533,
          "fileSize": 5552610,
          "channels": "stereo",
          "type": "audio",
          "format": "opus",
          "display": {"icon16x16": "yoto:#<iconMediaId>"}
        }],
        "display": {"icon16x16": "yoto:#<iconMediaId>"}
      }
    ]
  }
}
```

### Field semantics
- `cardId` — include to update an existing card; omit to create a new one (the response gives you the assigned `cardId`)
- `metadata.media.duration` / `.fileSize` — **sums** over all chapters (seconds, bytes). The Player uses these for whole-playlist scrubbing
- `metadata.media.readableFileSize` — MB rounded to 1 decimal; server keeps or strips it harmlessly
- `metadata.cover.imageL` — playlist cover shown in the Yoto app
- `content.activity` / `content.version` — present in the official Yoto web app's payloads; include them as shown
- `content.config.onlineOnly: false` — playlist plays from local download once synced
- `track.duration` — **integer seconds** (same unit as the transcode response, no conversion needed)
- `track.fileSize` — **bytes** (same value as the transcode response)
- `track.channels` — `"stereo"` or `"mono"`; detect from source MP3 with `ffprobe -show_entries stream=channels`
- `track.format` — **always `"opus"`** because Yoto transcodes everything to Opus, regardless of what you uploaded
- `track.overlayLabel` — required at the track level (not just chapter); typically the chapter number as a string
- `trackUrl` and `icon16x16` values both use the `yoto:#` scheme prefix on a Yoto media hash

### Response
```json
{
  "card": {
    "cardId": "ci8iF",
    "title": "...",
    "content": { ...full echo of chapters... },
    "metadata": { ...with server-added authors/narrators/etc. arrays... }
  }
}
```

Server auto-adds: `authors: []`, `narrators: []`, `copyrights: []`, `accents: []`, `abridged: false`. You can omit these in your POST.

## Other useful endpoints

### List your MYO cards
```
GET /content/mine
Authorization: Bearer {access_token}
```
Returns `{cards: [{cardId, title, metadata: {...}, ...}]}` — chapter list is omitted in summary view. For full content use `GET /content/{cardId}` (requires `user:content:view` or `family:library:view`).

### List devices (for MQTT subscribe)
```
GET /device-v2/devices/mine
Authorization: Bearer {access_token}
```
Requires `family:devices:view`. Returns `{devices: [{deviceId, name, deviceFamily, ...}]}`. The `deviceId` (format like `y23Ht5G9w5qhBpp3GZZakJPO`) is what goes in MQTT topics — it is NOT the same as the Player's "registration code" shown in the app.

## MQTT (diagnostics)

Yoto Players speak MQTT to an AWS IoT broker using a custom JWT authorizer. Useful for observing Player behaviour live — what chapter is playing, what `trackLength` the Player thinks each track has, errors, etc.

- Broker: `aqrphjqbp3u2z-ats.iot.eu-west-2.amazonaws.com:443`
- Transport: `websockets`
- Username: `_?x-amz-customauthorizer-name=PublicJWTAuthorizer`
- Password: access_token
- Topics: `device/{deviceId}/data/events`, `device/{deviceId}/data/status`, `device/{deviceId}/response`
- Publish `device/{deviceId}/command/status/request` (empty body) to force-push a status snapshot

Useful event fields:
- `trackLength` — seconds; **should match your `duration`**. If it's a small constant like 4 and tracks advance rapidly, your `track.format` is almost certainly wrong (see `pitfalls.md`)
- `position` — current playback position in seconds; should increment normally during playback
- `playbackStatus` — `playing`, `paused`, `stopped`
- `streaming` — `false` means Player is reading the locally-downloaded file (good); `true` would mean live streaming
- `cardId`, `chapterKey`, `trackKey`, `chapterTitle`, `trackTitle` — what the Player thinks is currently loaded
- `cardUpdatedAt` — server-side timestamp of last `/content` write; useful for verifying the Player has the latest metadata
- `freeDisk` — remaining storage (KB); Player has ~30 GB free typically; storage is rarely the issue

See `scripts/mqtt_log.py` for a self-contained MQTT subscriber.

## Limits

- **Hard cap: 100 chapters per playlist.** `POST /content` returns `400 "track count is limited to 100"`. Plan splits across multiple cards if needed.
- No published rate limits on uploads. Be polite: max 4 parallel audio uploads, max 8 parallel icon uploads. Back off on errors.
- Individual MP3s up to ~50 MB tested fine; larger transcode slower.
- Access tokens last 24 h. Refresh tokens require `offline_access` scope enabled in the dashboard.

## Physical card binding

There is no API for NFC bind. The user must scan the blank MYO card on the Player while the Yoto app is open and assign the new playlist from their library.
