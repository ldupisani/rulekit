# rulekit — agent entry point

**The project instructions live in [`CLAUDE.md`](CLAUDE.md). Read that file
first.** Everything there applies here unchanged:
the constitution, the commands, the layout, and the pointer to
`docs/README.md`.

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

Put shared project-wide rules in `CLAUDE.md` so Codex and Claude follow the
same contract. There are currently no Codex-specific additions.
