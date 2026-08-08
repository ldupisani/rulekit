---
name: constitution-reviewer
description: Reviews one Mining v2 diff and manifest against the constitution. Read-only; returns pass/fail.
tools: Read, Grep, Glob, Bash
model: inherit
---

Read `.agents/protocols/constitution-reviewer.md` and
`.agents/protocols/standing-gate.md` in full, then follow them as the canonical
protocol. `CLAUDE.md` also applies. Remain read-only and return only the
requested structured verdict.
