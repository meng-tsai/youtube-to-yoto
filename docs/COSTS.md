# Costs

This skill uses Claude SubAgents for two things:

1. **Subject extraction** (Phase 3) — Sonnet, ~20 SubAgents, very cheap.
2. **Sprite generation** (Phase 4) — Opus, one SubAgent per unique
   subject, the dominant cost.

What you pay depends entirely on **how you're billed for Claude**.

## On Claude Pro / Max subscription

**$0 extra.** SubAgent runs draw from your existing plan's hourly /
5-hour usage window.

| Plan | Quota window | Typical playlist of 100 episodes |
|---|---|---|
| Pro | 5-hour window | Tight — may hit the wall on a 100-episode bulk run mid-Phase-4. |
| Max 5× | 5-hour window | Comfortable — 100 episodes fit. |
| Max 20× | 5-hour window | Trivially comfortable. |

The skill's first-run demo mode (3 episodes) uses ~3-5% of a Pro
5-hour window. Use it first to confirm everything works before going
big.

If you hit the quota mid-run, the skill is resumable — partial
progress is in `upload_cache.json`. Wait for the window to roll over,
then re-run the same command.

## On pay-as-you-go Anthropic API key

Approximate per-sprite cost at current Opus pricing (Jan 2026 cutoff;
verify at https://www.anthropic.com/pricing):

| Sprite generation | ~7-10k input tokens + ~3-5k output tokens per SubAgent |
| Per sprite | ~$0.10 – $0.15 |
| 70 unique subjects (typical of 100 episodes after dedup) | **~$7 – $10** |

Subject extraction (Sonnet) is roughly $0.50 for a 100-episode batch.

The skill **always announces estimated cost up front** and asks for
your explicit "yes" before fanning out SubAgents. Partial cost (if you
say no halfway) is just what's already run, capped at the cached
state.

## On the free Claude tier

Not enough quota. The skill will likely bail mid-Phase-4 with a
quota-exceeded error. Upgrade to Pro before running, OR use an API
key.

## Why Opus and not Sonnet for sprites

Sonnet draws acceptable sprites for very simple subjects (`apple`,
`star`) but degrades quickly on anything with depth — a `rhinoceros
beetle` from Sonnet often looks like a generic bug, while Opus knows
to put a forward-curving horn on a black-armored body. Since sprite
quality is the only thing the user actually sees on the Player's
display, we default to Opus.

A future flag may offer a Sonnet fallback for cost-conscious users;
not in v1.

## Tracking actual usage

After every run, the skill prints a summary:

```
Phase 3 (subject extraction): 14 Sonnet SubAgents, ~ $0.50 API-equivalent
Phase 4 (sprite generation):  73 Opus SubAgents, ~ $9.20 API-equivalent
On Pro/Max: free within plan quota
```

For Pro/Max users this is just transparency — you're not actually
charged. For API users it's the real bill.
