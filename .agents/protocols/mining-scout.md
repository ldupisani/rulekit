# GSM8K Mining v2 scout — canonical protocol

You are read-only. Propose bounded general classes from inspectable GSM8K DEV;
never edit, create worktrees, or touch protected slices.

Read `AGENTS.md`, `.agents/protocols/standing-gate.md`, the active Mining v2
plan, current HANDOFF, methodology §§4–6/9, and negative results. Re-derive the
worklist from current `stats --slice dev-train`; historical counts are context,
not evidence.

## Selection

- Start with fully read declines and generated ask/premise coverage. Candidate
  text must be a nameable semantic class, not a shared phrase.
- Walk enough DEV-train item ids to identify the last blockers on both sides:
  facts the premises must emit and the ask/consumer that must use them.
- Prefer a narrow class with an honest small yield to a wide surface count.
- Do not propose a stand-alone zero-yield enabler. Fold it into the class that
  buys it, so benefit and risk share one gate.
- Check `packs/difg-mined/quarantine.yaml` for every vocabulary admission.
  Admit only words bound by the mechanism; record collision risk.
- Do not repeat a negative result unless a named blocker has since landed.
- Minimize overlap between candidates. Name shared files/functions explicitly.

## Output

Return JSON `{candidates, deferred, notes}`. Each candidate must contain all
fields needed by `CampaignCandidateManifest` except commit, fingerprint,
specimens, and captured traces: `slug`, `class_name`, `mechanism`,
`class_evidence`, `generation_contract`, `implementation_contract`, `risks`,
`review_ids`, `priority`, and `overlaps_with`.

For ordinary coverage, require all four specimen kinds: `strict_positive`,
`boundary_probe`, `answerable`, `decline`. Structural summaries paraphrase the
class and may cite DEV item ids, but must not quote corpus sentences.
