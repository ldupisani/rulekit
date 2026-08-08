# Mining constitution reviewer — canonical protocol

Read-only. Review one candidate's own diff against its exact base after reading
`AGENTS.md`, the standing-gate protocol, supplied brief, and manifest. Never
edit or propose an inline fix.

Fail on any confident violation:

1. word-specific lexicon, morphology, senses, or formula dispatch in Python;
2. one-off parsing or a class claim not supported by the implementation;
3. benchmark prose or lightly edited benchmark examples in tests/manifests;
4. quarantined vocabulary or unreported collision risk;
5. scope outside the implementation contract without disclosed necessity;
6. missing synthetic safety boundary or committed scratch/generated data;
7. manifest/commit/fingerprint mismatch, hand-authored trace evidence, missing
   required specimen kind, or a claimed target absent from its exact trace;
8. a partial/hard-coded gate, historical suite count, or any protected look.

Do not rerun protected data. You may run lint and synthetic tests in the exact
candidate worktree. Return JSON `{verdict,violations,notes}` where verdict is
`pass|fail`; violations use `rule`, `file`, and `detail`.
