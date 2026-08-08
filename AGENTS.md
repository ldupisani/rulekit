# rulekit — agent entry point

**The project instructions live in [`CLAUDE.md`](CLAUDE.md). Read that file
first, then the one delta below.** Everything there applies here unchanged:
the constitution, the commands, the layout, and the pointer to
`docs/HANDOFF.md`.

## Why this file does not repeat them

It used to. It was a byte-for-byte copy of `CLAUDE.md` apart from a single
path — 78 duplicated lines, including the whole constitution.

This repo has already paid for that pattern and written it down: a contract
with two copies has already drifted (`_ACCOUNTED_VALUE_KINDS` was defined
twice, the copies diverged, and it cost two review rounds; there is now ONE
definition in `answer.py` that `guards.py` imports). The invariant that came
out of it is blunter still — **prose does not enforce**: every rule that held
had to become a gate or a schema field, because docstrings and hand-copied
notes get routed around.

The constitution is the document least able to afford a second copy. If it is
edited in one file and not the other, two agents are working to different
rules and nothing detects it.

## The one delta

`CLAUDE.md`'s `/mine` section points at the Claude Code skill:

    .claude/skills/mine/SKILL.md

The Codex-native skill is at:

    .agents/skills/mine/SKILL.md

and its thin launch adapters are `.codex/agents/*.toml`. Both Codex and Claude
adapters read the one canonical protocol set in `.agents/protocols/`, removing
the previous duplicated, divergent agent bodies. The roles are
`mining-scout`, `mining-implementer`, `constitution-reviewer`,
`mining-integrator`, and `difg-corpus-planner`.

Nothing else differs. **If you find yourself about to add a second
project-wide rule here, put it in `CLAUDE.md` instead** — this file is for
what is genuinely Codex-specific, and today that is one path.
