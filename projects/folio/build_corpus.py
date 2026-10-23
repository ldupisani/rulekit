"""Materialize the FOLIO logic gate into GSM8K-shaped parquet.

Run once to (re)create data/folio_dev.parquet + data/folio_test.parquet:

    uv run --with datasets python projects/folio/build_corpus.py

INFRASTRUCTURE, not a throwaway mining script: the DEV/TEST split is defined by
SALT below, so the committed builder IS the definition of the firewall cut (see
projects/asdiv/build_corpus.py's docstring for the full argument).

WHY THIS CORPUS EXISTS. It is the SIXTH cross-corpus gate and the first that is
not arithmetic. Every other corpus asks for a number, so none of them can catch
the engine ASSERTING A NUMBER at logic prose. FOLIO (Han et al. 2022, Yale-LILY,
arxiv:2209.00840) is human-written natural-language first-order logic. It was
picked over ProofWriter/RuleTaker and LogiQA/ReClor by the four checks in
docs/corpora.md, all four MEASURED before wiring (2026-07-16):

  1. INDEPENDENT AUTHORS — Yale NLP annotators; never seen by our packs.
  2. BALANCED LABELS — True 38.8% / Uncertain 32.4% / False 28.9%. The
     majority-class NULL scores 38.8%, so this gate carries information. This is
     the check difg's own logic domain FAILS (8 of 8 prose yes/no golds are
     'Yes', so an always-yes engine scores 8/8 and the measurement is empty).
  3. NATURAL ENGLISH — 1,662 distinct premise skeletons over 5,286 sentences;
     the top skeleton is 0.2% of the pool. ProofWriter was REJECTED here, and the
     number is the reason: its 292,776 questions draw on a total vocabulary of
     52 WORD TYPES ("Gary is furry", "Bob is not blue"). Fitting a rule to that
     measures the generator, not reading — the MAWPS lesson (84% one template).
  4. VERIFIABLE GOLDS — every row carries premises-FOL/conclusion-FOL. NOTE the
     honest caveat: that FOL is human-written annotation, not an executable
     oracle (3.2% of conclusion-FOL strings do not even have balanced parens), so
     it is carried for AUDITING a disagreement, never as the gold itself. The
     gold is FOLIO's human-verified label.

THE GOLD MAPPING IS THE LOAD-BEARING DECISION, and it is a null-control guard:

  True/False -> `#### True` / `#### False`. parse_typed_gold classifies these
  kind='verdict' and _judge_typed compares them as BOOLEANS. Reachable in
  principle the day the kernel commits verdicts (Frontier 2).

  Uncertain  -> `#### Uncertain`, which lands as kind='text'. It is deliberately
  NOT mapped to a `decline` gold, and that is the whole point: a decline gold
  scores a DECLINING engine 'correct', so mapping Uncertain that way would hand
  an always-decline engine ~32% of this corpus for zero reasoning — difg's
  degenerate-measurement disease reappearing in a new place. As text, a decline
  scores 'declined' (neither correct nor wrong), which is the truth: FOLIO's
  'Uncertain' is the POSITIVE claim "this does not follow from the premises",
  which needs real inference. Not understanding a sentence is not the same as
  concluding uncertainty, and the harness must never confuse the two.

WHAT IT BUYS TODAY — with ZERO kernel or harness change. The engine has no
inference machinery, so it should DECLINE every item: expect 0 correct / 0 wrong,
exactly like SciBench. The value is the WRONG column: a committed NUMBER against
a verdict/text gold scores WRONG (_judge_typed's deliberate asymmetry), so if an
arithmetic ask ever fires on logic prose — and these premises are full of bindable
numbers ("published a book in 1946") — this gate is the only one that can see it.
A rising number here is the engine guessing.

FIREWALL — AND THE ONE PLACE THIS BUILDER DEPARTS FROM asdiv's. asdiv buckets on
the item's own text; that is WRONG here. FOLIO's 1,001 train rows share only 340
distinct PREMISE BLOCKS (mean 2.94 examples per story, one block reused 10x), so
a per-item hash would put one story's conclusions on BOTH sides of the firewall
and a TEST item's premises would already have been mined in DEV. The bucket key
is therefore the PREMISES BLOCK, so a whole story lands on one side. Per-item
hashing would have leaked 661 of 1,001 rows.

DETERMINISM. md5(SALT + premises) % 4 == 0 -> TEST (~25%), else DEV. No
Date/random: re-running is byte-identical.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SALT = "folio-test@1"          # load-bearing: the firewall cut. NEVER change it.
HERE = Path(__file__).resolve().parent

# FOLIO's three labels, normalized to the gold payloads described above. A label
# outside this map is not a label we are willing to score against -> the row is
# dropped, exactly as an unreadable float gold is.
_LABELS = {"true": "True", "false": "False", "uncertain": "Uncertain"}


def story_key(premises: str) -> str:
    """The firewall's unit: one premise block = one story = ONE side of the cut.

    Whitespace-normalized, and that is deliberate rather than cosmetic: the key
    must not be sensitive to formatting the item text already ignores (phrase()
    normalizes the same way), or a future re-export with reflowed newlines would
    silently re-bucket stories and move the cut under a spent TEST look.
    """
    return " ".join(str(premises).split())


def bucket(premises: str) -> str:
    """Bucket by STORY (the premise block), never per item — see the docstring."""
    h = hashlib.md5((SALT + story_key(premises)).encode()).hexdigest()
    return "test" if int(h, 16) % 4 == 0 else "dev"


def phrase(premises: str, conclusion: str) -> str:
    """Premises verbatim, then ONE fixed interrogative wrapper.

    The wrapper is the only templated text in the item; the premises and the
    conclusion are FOLIO's human-written prose, untouched. The conclusion keeps
    its original capitalization on purpose: lower-casing its first word would
    corrupt the proper nouns these items turn on ("Miroslav Venhoda loved
    music."), and deciding which first words are safe to fold would mean a word
    list, which is the thing the constitution forbids.

    The wrapper text is part of the hashed corpus contract only via the premises
    (see bucket()), but it is still frozen: re-wording it re-reads every item.
    """
    concl = " ".join(str(conclusion).split()).rstrip(".")
    return f"{story_key(premises)} Is it true that {concl}?"


def main() -> None:
    from datasets import load_dataset  # only the fetch needs it; the split logic doesn't

    ds = load_dataset("tasksource/folio")
    rows = list(ds["train"]) + list(ds["validation"])

    dev_q, dev_a, dev_s, test_q, test_a, test_s = [], [], [], [], [], []
    dropped = 0
    for r in rows:
        label = _LABELS.get(str(r["label"]).strip().lower())
        if label is None or not str(r.get("premises", "")).strip():
            dropped += 1
            continue
        text = phrase(r["premises"], r["conclusion"])
        answer = f"#### {label}"
        story = story_key(r["premises"])
        if bucket(str(r["premises"])) == "test":
            test_q.append(text); test_a.append(answer); test_s.append(story)
        else:
            dev_q.append(text); dev_a.append(answer); dev_s.append(story)

    (HERE / "data").mkdir(exist_ok=True)
    for name, qs, ans, st in (
        ("folio_dev", dev_q, dev_a, dev_s),
        ("folio_test", test_q, test_a, test_s),
    ):
        # `story` is the holdout-grouping column (project.yaml `group: story`):
        # the INTERNAL dev-train/dev-holdout cut must bucket by premise block
        # for the same reason the DEV/TEST cut does — 340 stories share 1,001
        # rows, and a per-item hash puts one story's conclusions on both sides.
        # DEV/TEST membership itself still comes from bucket() above, untouched.
        table = pa.table({"question": qs, "answer": ans, "story": st})
        out = HERE / "data" / f"{name}.parquet"
        pq.write_table(table, out)
        print(f"  {name:10} {len(qs):5d} items -> {out}")
    print(f"dropped {dropped} rows with an unreadable label/premise")
    print(f"DEV is the standing gate; TEST ({len(test_q)}) is one-look-only.")


if __name__ == "__main__":
    main()
