# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.0.1] — 2026-06-28

### Fixed
- **Chapter titles on the Yoto Player no longer show raw YouTube SEO noise** (channel/season prefix + hashtags). Phase 3 SubAgent now extracts a clean native-language story title alongside the English sprite subject — `subjects.json` schema upgraded to `{vid: {subject, title}}`. `yoto_upload.py` reads the per-episode title from there and overrides the manifest's raw YouTube title. Legacy flat `{vid: "subject"}` still works (with a warning).

### Changed
- `references/subagent-prompts.md` — Phase 3 prompt updated with title-cleaning rules + worked examples.
- `scripts/yoto_upload.py` — accepts both the new dict format and the legacy flat format in `subjects.json`.
- `SKILL.md` — Phase 3 description updated to document the dual-extraction step.
- `references/pitfalls.md` — added "Never use raw YouTube title verbatim" with symptom + fix.

## [1.0.0] — 2026-06-27

### Added
- Initial public release of the youtube-to-yoto skill.
- Dual install surface: Claude Code plugin (`/plugin install`) and vercel-labs/skills (`npx skills add`).
- Newcomer-friendly onboarding via `docs/SETUP.md`.
- Conversational OAuth walkthrough (`references/oauth-setup.md`).
- Idempotent dependency bootstrap (`scripts/bootstrap.sh`).
- Cost-transparency gate before sprite-generation subagent fan-out.
- First-run demo recommendation (3 episodes before full playlist).
- README in English plus 6 community-language mirrors.
