"""GOLDEN MASTER for answer.py's 41 consumers — characterisation, not design.

WHAT THIS IS FOR. `answer.py` is 3,479 lines against architecture.md's "≤ ~400",
and splitting it by consumer is the refactor the size argues for. It is also
the riskiest change available here: `answer.py` is where every guard lives, and
a broken GUARD is the failure the corpus gates cannot see — "the corpus gate
cannot see a contract no corpus phrases". A happy path that breaks shows up as
a lost `correct`; a guard that breaks shows up as a confident WRONG, or as
nothing at all.

So this file pins CURRENT behaviour, right or wrong. It is not a statement that
these answers are desirable — several are declines from guards whose message is
the only thing distinguishing them. A refactor that preserves behaviour leaves
every row untouched; a refactor that changes one has to say so deliberately.

THE ROWS ASSERT WHICH CONSUMER WAS REACHED, and that is the point rather than
decoration. Without it a probe that silently stops routing to its consumer
would keep passing while testing nothing — the vacuous-test trap, which this
session hit twice (a decline asserted through `solve()` that declined
identically before and after because the probe never reached the shape). The
consumer comes from `match_ask`, the same function `answer()` dispatches on, so
the assertion is on the real dispatch and not a reimplementation of it.

COVERAGE IS PARTIAL AND MEASURED: 41 consumers, 102 probes — 24 answering
paths and 78 GUARDS — reaching 45 of the 92 distinct guard messages in
`answer.py` (49%). The probes were mined from the existing suite, so they reach
exactly the guards the suite already reached; the other 47 need hand-written
inputs. `test_guard_coverage_does_not_regress` pins the number and names the
gaps, so the figure cannot rot and a refactor of any consumer can see which of
ITS guards are unprotected before it starts. Probes were mined by instrumenting dispatch
during the existing suite, then filtered so that NO probe contains a corpus
sentence (constitution rule 3); the generator applies that filter itself, so it
cannot reintroduce at scale what was just cleaned out of tests/.

REASONS ARE MATCHED BY PREFIX, up to the first ':' or ' but '. The tail carries
entity names and values that legitimately vary; the prefix identifies WHICH
guard fired, which is the thing worth pinning.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import match_ask

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def registries():
    return {n: load_project(ROOT / "projects" / n).registry
            for n in ("gsm8k", "difg", "scratch")}


# (registry, question, expected consumer, kind, value, reason prefix)
GOLDEN = [
    ('gsm8k', 'Convert 0 degrees Celsius to Fahrenheit.',
     'affine-convert', 'number', 32.0, 'affine-convert'),
    ('gsm8k', 'Convert 100 degrees Fahrenheit to Kelvin.',
     'affine-convert', 'decline', None, "no known scale conversion from 'fahrenheit' to 'kelv"),
    ('gsm8k', 'Convert 100 degrees Rankine to Celsius.',
     'affine-convert', 'decline', None, "no known scale conversion from 'rankine' to 'celsius"),
    ('gsm8k', 'How old will Deja be 6 years from now?',
     'age-projected', 'decline', None, "no year quantity known for 'deja'"),
    ('gsm8k', 'How old will Sara be in 5 years?',
     'age-projected', 'decline', None, "no year quantity known for 'sara'"),
    ('gsm8k', 'how old will Mateo be after 4 years?',
     'age-projected', 'decline', None, "no year quantity known for 'mateo'"),
    ('gsm8k', 'What is 1,234 plus 1?',
     'arithmetic', 'number', 1235.0, 'arithmetic'),
    ('gsm8k', 'What is 7 divided by 0?',
     'arithmetic', 'decline', None, "'divide' not defined for the given inputs"),
    ('gsm8k', 'What is the percentage increase from 0 to 50?',
     'arithmetic', 'decline', None, "'percent_change' not defined for the given inputs"),
    ('gsm8k', 'Determine the average weight of the four people.',
     'average', 'decline', None, "measure 'weight' is ambiguous across the facts"),
    ('gsm8k', 'What is the average number of fish they caught?',
     'average', 'decline', None, "a combined ask needs at least two holders of 'fish';"),
    ('gsm8k', 'How many days are between 1 Jan 2024 and 31 Jan 2024?',
     'calendar', 'number', 30.0, 'calendar'),
    ('gsm8k', 'What is the day of the year for 2024-13-45?',
     'calendar', 'decline', None, "'2024-13-45' is not a readable date"),
    ('gsm8k', 'How many kites can Farid buy with 12 dollars?',
     'capacity', 'decline', None, "0 price facts known for 'kite' — a capacity ask need"),
    ('gsm8k', 'How many pens can Mary buy with 0.3 dollars?',
     'capacity', 'decline', None, "0 price facts known for 'pen' — a capacity ask needs"),
    ('gsm8k', 'How many snacks can Delia buy with 10 dollars?',
     'capacity', 'decline', None, "0 price facts known for 'snack' — a capacity ask nee"),
    ('gsm8k', 'How much change did Callum get?',
     'change', 'decline', None, "0 tender facts known for 'callum' — a change ask nee"),
    ('gsm8k', 'How much change did Harriet receive?',
     'change', 'decline', None, "0 tender facts known for 'harriet' — a change ask ne"),
    ('gsm8k', 'How much change did Owen get?',
     'change', 'decline', None, "0 tender facts known for 'owen' — a change ask needs"),
    ('gsm8k', 'Calculate their combined balance.',
     'combined', 'decline', None, "measure 'balance' is ambiguous across the facts"),
    ('gsm8k', 'Calculate their combined height.',
     'combined', 'decline', None, "measure 'height' is ambiguous across the facts"),
    ('gsm8k', 'Determine their combined age.',
     'combined', 'decline', None, "measure 'age' is ambiguous across the facts"),
    ('gsm8k', 'How many do Priya and Wendell have combined?',
     'combined-elided-measure', 'decline', None, "'priya' and 'wendell' share 0 measures — an elided-m"),
    ('gsm8k', 'What is the distance between (0,0) and (8,15)?',
     'coordinate', 'number', 17.0, 'coordinate'),
    ('gsm8k', 'What is the distance between (1,1) and (4,5,9)?',
     'coordinate', 'decline', None, "'distance' needs two points of equal arity"),
    ('gsm8k', 'What is the slope between (3,1) and (3,9)?',
     'coordinate', 'decline', None, "'slope' not defined for the given points"),
    ('gsm8k', 'How much did Rosa pay for 6 candles?',
     'cost-of-quantity', 'decline', None, "0 price facts known for 'candle' — a cost-of-quantit"),
    ('gsm8k', 'How much did Rosa pay for 6 pencils?',
     'cost-of-quantity', 'decline', None, "0 price facts known for 'pencil' — a cost-of-quantit"),
    ('gsm8k', 'How much did Wendell spend on 3 mugs?',
     'cost-of-quantity', 'decline', None, "0 price facts known for 'mug' — a cost-of-quantity a"),
    ('gsm8k', 'How many more apples does Tom need?',
     'deficit', 'decline', None, "0 goal facts known for 'tom'/'apple' — a deficit ask"),
    ('gsm8k', 'How many more cookies does Marcus need?',
     'deficit', 'decline', None, "0 goal facts known for 'marcus'/'cookie' — a deficit"),
    ('gsm8k', 'How many more stamps does Lena need?',
     'deficit', 'decline', None, "0 goal facts known for 'lena'/'stamp' — a deficit as"),
    ('gsm8k', 'How many inches taller is Noor than her brother?',
     'difference', 'decline', None, "missing a total for 'noor' or 'brother'"),
    ('gsm8k', 'How many inches taller is Priya than her cousin?',
     'difference', 'decline', None, "missing a total for 'priya' or 'cousin'"),
    ('gsm8k', 'How many more apples did Mary sell than Tom?',
     'difference', 'decline', None, "missing a total for 'mary' or 'tom'"),
    ('gsm8k', 'What is 25% off $80 then 0% tax?',
     'discounted-total', 'number', 60.0, 'discounted-total'),
    ('gsm8k', 'What is 100% off $80?',
     'discounted-total', 'decline', None, '1.0 is not a usable discount'),
    ('gsm8k', 'What is 150% off $80?',
     'discounted-total', 'decline', None, '1.5 is not a usable discount'),
    ('scratch', 'Is it true that A dog eats apples?',
     'existential-verdict', 'verdict', 'undetermined', 'no witness and no refuting universal'),
    ('gsm8k', 'What is the area of a circle with radius 10?',
     'geometry', 'number', 314.16, 'geometry'),
    ('gsm8k', 'What is the area of a circle with length 5?',
     'geometry', 'decline', None, "'area' of a 'circle' needs dimensions its given ones"),
    ('gsm8k', 'What is the perimeter of a circle with radius 5?',
     'geometry', 'decline', None, "no geometry formula for 'perimeter' of a 'circle'"),
    ('gsm8k', 'How much do the jackets cost?',
     'item-cost', 'decline', None, "0 price facts known for 'jacket' — an item-cost ask "),
    ('gsm8k', 'How much does a hat cost?',
     'item-cost', 'decline', None, "0 price facts known for 'hat' — an item-cost ask nee"),
    ('gsm8k', 'How much does the scarf cost?',
     'item-cost', 'decline', None, "0 price facts known for 'scarf' — an item-cost ask n"),
    ('gsm8k', 'How many more apples than oranges are there?',
     'label-difference', 'decline', None, "'apple'/'orange' need exactly one SHARED holder — fo"),
    ('gsm8k', 'How many more birds than fish are there?',
     'label-difference', 'decline', None, "'bird'/'fish' need exactly one SHARED holder — found"),
    ('gsm8k', 'How many more cats than dogs are there?',
     'label-difference', 'decline', None, "'cat'/'dog' need exactly one SHARED holder — found ["),
    ('gsm8k', 'What is the average of 10, 20, and 30?',
     'list-statistic', 'number', 20.0, 'list mean of 3 values'),
    ('gsm8k', 'What is the highest of 11, 46, 8, and 34?',
     'list-statistic', 'number', 46.0, 'list highest of 4 values'),
    ('gsm8k', 'What is the mode of 1, 1, 2, and 2?',
     'list-statistic', 'decline', None, "'mode' is not unique"),
    ('scratch', 'Is it true that Rex is a dog or a cat?',
     'logic-disjunction-verdict', 'verdict', 'undetermined', "inclusive-or undecided; open world has 'dog'=None 'c"),
    ('scratch', 'Is it true that Rex is either a dog or a cat?',
     'logic-disjunction-verdict', 'verdict', 'undetermined', 'exclusive-or needs BOTH disjunct truths; open world '),
    ('scratch', 'Is it true that Ana is a Rovers player?',
     'logic-verdict', 'verdict', 'undetermined', 'no logic fact decides it'),
    ('gsm8k', 'How much to fence a 10 by 20 yard at $3 per meter plus 10% tax?',
     'measure-cost', 'number', 198.0, 'measure-cost'),
    ('gsm8k', 'How much does it cost to fence a 10 by 20 yard at $3 per meter?',
     'measure-cost', 'decline', None, "[ambiguity] 'much' stayed ambiguous (sentence 0)"),
    ('gsm8k', 'How much to fence a 0 by 20 yard at $3 per meter?',
     'measure-cost', 'decline', None, 'a measure must be positive'),
    ('gsm8k', 'Is Ana a student?',
     'membership-verdict', 'verdict', 'undetermined', 'no membership fact either way'),
    ('gsm8k', 'Is Mary a student at Yale?',
     'membership-verdict', 'decline', None, "question names ['yale']"),
    ('gsm8k', 'How many moles are in 90.075 grams of H2O?',
     'molar-mass', 'number', 5.0, 'molar-mass'),
    ('gsm8k', 'How much money does Desmond have left?',
     'money-left', 'decline', None, "no resolvable 'currency' total for 'desmond'"),
    ('gsm8k', 'How much money does Grant have left?',
     'money-left', 'decline', None, "no resolvable 'currency' total for 'grant'"),
    ('gsm8k', 'How much money does Nadia have left?',
     'money-left', 'decline', None, "no resolvable 'currency' total for 'nadia'"),
    ('gsm8k', 'What is 5 choose 2?',
     'number-theory', 'number', 10.0, 'number-theory'),
    ('gsm8k', 'What is 3 choose 8?',
     'number-theory', 'decline', None, "'choose' not defined for the given inputs"),
    ('gsm8k', 'What is the GCD of 12?',
     'number-theory', 'decline', None, "'gcd' not defined for the given inputs"),
    ('gsm8k', 'How many apples are not red?',
     'partition-complement', 'decline', None, "0 partition facts known for 'apple'/'red'"),
    ('gsm8k', 'How many birds are not yellow?',
     'partition-complement', 'decline', None, "0 partition facts known for 'bird'/'yellow'"),
    ('gsm8k', 'How many green marbles are there?',
     'partition-complement', 'decline', None, "0 partition facts known for 'marble'/'green'"),
    ('scratch', 'Is it true that Oxford Circus is designed by a British musician?',
     'passive-agent-verdict', 'verdict', 'undetermined', 'no agent relation decides it'),
    ('gsm8k', 'What is the speed of an object that took 4 seconds to travel 60 meters?',
     'physics', 'number', 15.0, 'physics'),
    ('gsm8k', 'What is the speed of an object that travels 60 meters in 4 seconds and 3 minutes?',
     'physics', 'decline', None, "'speed' cannot read the stated '3 minutes'"),
    ('gsm8k', 'What is the speed of an object that travels 60 meters in 4 seconds three times?',
     'physics', 'decline', None, "'speed' cannot read the stated 'three times'"),
    ('gsm8k', 'What is the speed of an object that travels 60 meters in twice 4 seconds?',
     'physics', 'decline', None, "'speed' cannot read the stated 'twice'"),
    ('gsm8k', 'What is the cost of 20 kilometers at $2 per km?',
     'rate-cost', 'number', 40.0, 'rate-cost'),
    ('gsm8k', 'What is the cost of 100 yards at $3 per km?',
     'rate-cost', 'decline', None, "no known conversion from 'yard' to 'kilometer'"),
    ('gsm8k', 'What is the cost of 20 miles at $2 per gallon?',
     'rate-cost', 'decline', None, "no known conversion from 'mile' to 'gallon'"),
    ('gsm8k', 'How many berries does the bird eat in 4 days?',
     'rate-span', 'decline', None, "0 rates known for 'bird'/'berry' — the span ask need"),
    ('gsm8k', 'How many coins does Tom find in 5 days?',
     'rate-span', 'decline', None, "0 rates known for 'tom'/'coin' — the span ask needs "),
    ('gsm8k', 'How many coins does the machine make in 3 days?',
     'rate-span', 'decline', None, "0 rates known for 'machine'/'coin' — the span ask ne"),
    ('gsm8k', 'How long did it take Omar to build 20 chairs?',
     'rate-span-inverse', 'decline', None, "0 rates known for 'omar'/'chair' — the inverse span "),
    ('gsm8k', 'How long did it take Sana to read 20 pages?',
     'rate-span-inverse', 'decline', None, "0 rates known for 'sana'/'page' — the inverse span a"),
    ('gsm8k', 'How long does it take Nora to bake all cookies?',
     'rate-span-inverse', 'decline', None, "0 rates known for 'nora'/'cookie' — the inverse span"),
    ('gsm8k', 'How many apples are in the bowl?',
     'single-entity', 'decline', None, "no quantity known for 'bowl' of 'apple' (ask ask/how"),
    ('gsm8k', 'How many apples did Carla eat?',
     'single-entity', 'decline', None, "no 'eat' events known for 'carla'/'apple'"),
    ('gsm8k', 'How many apples did Sam eat?',
     'single-entity', 'decline', None, "no 'eat' events known for 'sam'/'apple'"),
    ('gsm8k', 'How many did Oscar make?',
     'single-entity-elided-measure', 'decline', None, "'oscar' holds 0 measures — an elided-measure ask nee"),
    ('gsm8k', 'How many does Priya have?',
     'single-entity-elided-measure', 'decline', None, "'priya' holds 0 measures — an elided-measure ask nee"),
    ('gsm8k', 'What is the cosine of 0 degrees?',
     'trigonometry', 'number', 1.0, 'trigonometry'),
    ('gsm8k', 'What is the tangent of -90 degrees?',
     'trigonometry', 'decline', None, "'tan' not defined for the given inputs"),
    ('gsm8k', 'How many apples are there?',
     'unique-entity', 'decline', None, "0 entities hold 'apple' — an entity-less ask needs e"),
    ('gsm8k', 'How many books are there?',
     'unique-entity', 'decline', None, "0 entities hold 'book' — an entity-less ask needs ex"),
    ('gsm8k', 'How many bottles of oil are there?',
     'unique-entity', 'decline', None, "0 entities hold 'bottle' — an entity-less ask needs "),
    ('gsm8k', 'Convert 10 pounds to kg',
     'unit-convert', 'number', 4.5359237, 'unit-convert'),
    ('gsm8k', 'How many gallons are in 3 kilometers?',
     'unit-convert', 'decline', None, "no known conversion from 'kilometer' to 'gallon'"),
    ('gsm8k', 'How many moles are in 90 grams of Xx2O?',
     'unit-convert', 'decline', None, "no known conversion from 'gram' to 'moles'"),
    ('gsm8k', 'How many seconds are in 3 gallons?',
     'unit-convert', 'decline', None, "no known conversion from 'gallon' to 'second'"),
    ('gsm8k', 'How much does each kite cost?',
     'unit-price-from-total', 'decline', None, "no resolvable grand-total residual for 'kite' — need"),
    ('scratch', 'Is it true that All dogs are mammals?',
     'universal-verdict', 'verdict', 'undetermined', 'no universal fact and no counterexample'),
    ('gsm8k', 'What is the dot product of (1, 0, 2) and (3, 7, 4)?',
     'vector', 'number', 11.0, 'vector'),
    ('gsm8k', 'What is the dot product of (1, 2, 3) and (4, 5)?',
     'vector', 'decline', None, 'a dot product needs two equal-length vectors'),
    ('scratch', 'Is it true that Rex does not play for a farmer?',
     'verbal-obj-class-verdict', 'verdict', 'undetermined', 'no object-class relation decides it'),
]


def _reason_prefix(reason: str) -> str:
    return (reason or "").split(":")[0].split(" but ")[0].strip()[:52]


@pytest.mark.parametrize(
    "reg_name, text, consumer, kind, value, reason",
    GOLDEN,
    ids=[f"{row[2]}-{i}" for i, row in enumerate(GOLDEN)],
)
def test_consumer_behaviour_is_unchanged(registries, reg_name, text, consumer, kind, value, reason):
    reg = registries[reg_name]
    res = solve(text, reg, tracing=False)

    # 1. the probe still ROUTES where it did. Without this the rest can pass
    #    while measuring a completely different code path.
    assert res.question is not None, f"no question reading: {text!r}"
    matched = match_ask(res.question, reg)
    assert matched is not None, f"no ask matches any more: {text!r}"
    assert matched[1].get("consumer") == consumer, (
        f"{text!r} now routes to {matched[1].get('consumer')!r}, not {consumer!r}"
    )

    # 2. and still behaves the same
    assert res.answer.kind == kind
    if isinstance(value, float):
        assert res.answer.value == pytest.approx(value)
    else:
        assert res.answer.value == value
    assert _reason_prefix(res.answer.reason) == reason


def test_every_consumer_is_represented(registries):
    """The file is only a safety net for the consumers it actually covers.

    If a new consumer is added to answer.py without a row here, the refactor it
    is meant to protect would proceed with a blind spot — so failing loudly is
    the point.
    """
    import re

    src = (ROOT / "src" / "rulekit" / "kernel" / "answer.py").read_text()
    declared = set(re.findall(r'if consumer == "([a-z-]+)":', src))
    covered = {row[2] for row in GOLDEN}
    assert not (declared - covered), f"consumers with no golden row: {sorted(declared - covered)}"


def test_the_guards_are_the_bulk_of_the_coverage():
    """A characterisation suite weighted toward happy paths would miss the
    failure it exists for: a broken guard becomes a confident WRONG, which the
    corpus gates may never phrase."""
    guards = sum(1 for row in GOLDEN if row[3] == "decline")
    assert guards >= 2 * (len(GOLDEN) - guards), (
        f"only {guards} of {len(GOLDEN)} rows are guards"
    )


# --- the coverage of this file, measured and enforced ----------------------

_GUARD_FLOOR = 49   # guards WITH a probe: raise as probes are added, never lower
_GAP_CEILING = 43   # guards WITHOUT one: lower as probes are added, never raise

# Guards with no golden probe because they are UNREACHABLE from text by design
# (a defensive re-check, or a slot type that cannot bind the bad value). They
# are covered by direct unit tests on the extracted consumer instead — which is
# only possible once a consumer IS extracted. Listing them here keeps the
# coverage figure honest in both directions: they are not gaps, and they are
# not silently absent either.
_COVERED_BY_UNIT_TEST = {
    ("molar-mass", "no atomic mass known for"),
    ("molar-mass", "a cost needs a numeric rate"),
    ("molar-mass", "weight needs the gram->kilogram conversi"),
    ("molar-mass", "weight formula failed"),
}


def _declared_guards() -> dict[str, set[str]]:
    """Distinct decline messages per consumer, across the WHOLE consumer surface.

    ⚠ It scans `kernel/consumers/` as well as `answer.py`, and that is not
    tidiness. If it read only `answer.py`, EXTRACTING a consumer would delete
    its guards from the denominator and the coverage figure would improve for
    free — the refactor would launder away its own debt. Guards must stay
    counted wherever they live.
    """
    import re

    text = (ROOT / "src" / "rulekit" / "kernel" / "answer.py").read_text()
    extracted = {}
    consumers_dir = ROOT / "src" / "rulekit" / "kernel" / "consumers"
    if consumers_dir.is_dir():
        for mod in sorted(consumers_dir.glob("*.py")):
            if mod.name == "__init__.py":
                continue
            body = mod.read_text()
            m = re.search(r'@consumer\("([a-z-]+)"\)', body)
            if not m:
                continue
            msgs = re.findall(r'"decline",\s*None,\s*\n?\s*f?"([^"]{6,70})', body)
            extracted[m.group(1)] = {x.split("{")[0].split(":")[0].strip()[:40] for x in msgs}

    lines = text.split("\n")
    blocks, cur, start = {}, None, 0
    for i, ln in enumerate(lines):
        m = re.match(r'    if consumer == "([a-z-]+)":', ln)
        if m:
            if cur:
                blocks[cur] = "\n".join(lines[start:i])
            cur, start = m.group(1), i
    if cur:
        blocks[cur] = "\n".join(lines[start:])
    out = {}
    for consumer, body in blocks.items():
        msgs = re.findall(r'"decline",\s*None,\s*\n?\s*f?"([^"]{6,70})', body)
        out[consumer] = {m.split("{")[0].split(":")[0].strip()[:40] for m in msgs}
    out.update(extracted)
    return out


def guard_gaps() -> list[tuple[str, str]]:
    covered: dict[str, set[str]] = {}
    for row in GOLDEN:
        covered.setdefault(row[2], set()).add(row[5])
    gaps = []
    for consumer, guards in sorted(_declared_guards().items()):
        have = covered.get(consumer, set())
        for g in sorted(guards):
            if (consumer, g) in _COVERED_BY_UNIT_TEST:
                continue
            if not any(g[:24] in h or h[:24] in g for h in have):
                gaps.append((consumer, g))
    return gaps


def test_guard_coverage_does_not_regress():
    """A characterisation net is only as good as the guards it reaches, and
    that number is the kind of thing that rots silently.

    Enforcing it means adding a guard to `answer.py` without a probe FAILS
    here — which is the right moment to notice, not after a refactor has
    already moved the code.
    """
    total = sum(len(v) for v in _declared_guards().values())
    gaps = guard_gaps()
    reached = total - len(gaps)

    # BOTH directions, because either alone is fooled. The reached-count alone
    # misses a NEW unprotected guard alone: adding one raises `total` and
    # `gaps` together and leaves `reached` untouched — this test asserted
    # exactly that and passed a new unprotected guard until the injection
    # caught it. The gap-count alone would miss a probe being deleted while a
    # guard is deleted with it.
    assert reached >= _GUARD_FLOOR, (
        f"guard coverage fell to {reached}/{total} (floor {_GUARD_FLOOR})"
    )
    assert len(gaps) <= _GAP_CEILING, (
        f"{len(gaps)} guards now have no probe (ceiling {_GAP_CEILING}) — a new "
        f"guard needs a golden row. Newest gaps: {gaps[-5:]}"
    )


def test_the_unprotected_guards_are_listed_not_forgotten():
    """The gap is real and belongs in the open: ~half of answer.py's guards
    have no probe. This test always passes — it exists so the list is printed
    by `pytest -rA` and so the refactor of any consumer can see which of its
    guards it is about to move blind."""
    gaps = guard_gaps()
    print(f"\n{len(gaps)} guards with no golden probe:")
    for consumer, msg in gaps:
        print(f"  {consumer:26s} {msg}")
