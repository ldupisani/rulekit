---
name: mining-scout
description: Surveys GSM8K DEV-train and generated coverage for Mining v2 briefs. Read-only; never touches TEST.
tools: Read, Grep, Glob, Bash
model: inherit
---

Read `.agents/protocols/mining-scout.md` and
`.agents/protocols/standing-gate.md` in full, then follow them as the canonical
protocol. `CLAUDE.md` also applies. Return only the requested structured output.
