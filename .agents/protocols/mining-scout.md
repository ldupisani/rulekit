# GSM8K Mining v2 scout — canonical protocol

You are read-only. Propose bounded general classes from inspectable GSM8K DEV;
never edit, create worktrees, or touch protected slices.

Read `AGENTS.md`, `.agents/protocols/standing-gate.md`, the active Mining v2
plan, current HANDOFF, methodology §§4–6/9, and negative results. Re-derive the
worklist from current `stats --slice dev-train`; historical counts are context,
not evidence.

## Example-led selection

- Select one currently declining DEV-train item per requested candidate. Start
  with fully read declines where possible, but do not require three examples
  or a frequency threshold before proposing useful general language support.
- Walk that item end to end: missing vocabulary, premise facts, inference,
  ask bindings, answer contract, and every current final blocker. Candidate
  text must still be a nameable semantic class, not a one-question branch.
- Set coverage evidence honestly. A one-item pool with one expected solve is a
  valid starting point when invented specimens demonstrate the wider class.
- Specify invented strict-positive, paraphrase, boundary, complete-answerable,
  and deliberate-decline shapes. Never use corpus prose for those specimens.
- Require the implementer to pass synthetic evidence first, then reload the
  selected original item locally by id as a post-synthetic acceptance check.
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

For ordinary coverage, require all four manifest specimen kinds:
`strict_positive`, `boundary_probe`, `answerable`, `decline`; the strict and
answerable evidence must collectively include an invented surface paraphrase.
Structural summaries may cite DEV item ids, but must not quote corpus
sentences.
