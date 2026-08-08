---
name: mine
description: Run or resume one GSM8K Mining v2 batch with generated evidence, Designer human review, exact machine gates, constitution review, and sequential integration. Stops before protected TEST and never merges main.
argument-hint: "[count] [--smoke] [--integrate-approved]"
---

# /mine — Claude adapter

Read `.agents/skills/mine/SKILL.md` in full and execute that canonical Mining
v2 protocol using Claude's registered agents. Treat each instruction to spawn a
named role as a task for the matching `.claude/agents/*.md` adapter. Agent
behavior itself lives only in `.agents/protocols/`; do not recreate or override
it here.

The old JavaScript workflow was removed because it embedded obsolete corpus,
schema, historical-count, and automatic-integration policy. Do not look for or
recreate `.claude/workflows/mine.js`.
