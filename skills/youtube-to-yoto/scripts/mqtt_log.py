#!/usr/bin/env python3
"""
Live MQTT log of all events from the Yoto Player.

Subscribes to:
  device/{id}/data/events   — playback events, track changes, errors
  device/{id}/data/status   — periodic status (battery, wifi, online)
  device/{id}/response      — replies to commands

Auth: AWS IoT custom authorizer (PublicJWTAuthorizer), password = access_token.
Run in background and insert the card to watch what the Player reports.

    python3 mqtt_log.py
"""

import asyncio, json, sys, time, uuid
from pathlib import Path
import aiomqtt, requests

BROKER = "aqrphjqbp3u2z-ats.iot.eu-west-2.amazonaws.com"
PORT   = 443
AUTH   = "PublicJWTAuthorizer"

def short(s, n=300):
    if isinstance(s, (dict, list)):
        s = json.dumps(s, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + f"…(+{len(s)-n})"

def stamp():
    return time.strftime("%H:%M:%S")

async def main():
    token = json.load(open(str(Path.home() / ".yoto-tokens.json")))["access_token"]

    # Discover all devices on account (needs family:devices:view scope)
    r = requests.get("https://api.yotoplay.com/device-v2/devices/mine",
                     headers={"Authorization": f"Bearer {token}"}, timeout=15)
    r.raise_for_status()
    devices = r.json().get("devices", [])
    dev_ids = [d["deviceId"] for d in devices]
    names = {d["deviceId"]: d.get("name","?") for d in devices}
    for d in devices:
        print(f"  {d.get('name','?'):8s}  {d['deviceId']}  ({d.get('deviceFamily','?')})")
    print(f"[{stamp()}] tracking → {len(dev_ids)} device(s)\n")

    async with aiomqtt.Client(
        hostname=BROKER,
        port=PORT,
        username=f"_?x-amz-customauthorizer-name={AUTH}",
        password=token,
        identifier=f"YOTOAPI{uuid.uuid4().hex}",
        tls_params=aiomqtt.TLSParameters(),
        keepalive=60,
        transport="websockets",
    ) as client:
        for dev_id in dev_ids:
            for suf in ("data/events", "data/status", "response"):
                await client.subscribe(f"device/{dev_id}/{suf}")
            await client.publish(f"device/{dev_id}/command/status/request")
            await client.publish(f"device/{dev_id}/command/events/request")
        print(f"[{stamp()}] subscribed all devices; LIVE — insert the card now\n")

        async for msg in client.messages:
            parts = str(msg.topic).split("/")
            dev = parts[1] if len(parts) > 1 else "?"
            topic = "/".join(parts[2:]) if len(parts) > 2 else ""
            try:
                body = json.loads(msg.payload.decode())
            except Exception:
                body = msg.payload.decode(errors="replace")
            print(f"[{stamp()}] {names.get(dev,dev[:8]):8s} {topic:18s}  {short(body, 400)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
