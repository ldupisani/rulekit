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

COVERAGE IS COMPLETE AND MEASURED: 46 consumers, 177 probes — 28 answering
or verdict paths and 149 guard paths — reaching all 116 distinct guard
messages across the consumer surface: 107 from text rows here, 42 via direct unit probes
(`_COVERED_BY_UNIT_TEST` + tests/test_consumer_guard_probes.py, for guards
text cannot phrase — the reason is stated per entry). The first 102 probes
were mined from the existing suite; the session-4 rows were found by probing
the live matcher for each remaining gap. `test_guard_coverage_does_not_regress`
pins both directions, so the figure cannot rot and a new guard without a probe
fails loudly. Probes were mined by instrumenting dispatch
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
            for n in ("gsm8k", "difg", "scratch", "curated")}


# (registry, question, expected consumer, kind, value, reason prefix)
GOLDEN = [
    ('curated', 'Aven has 8 cards. How many red cards does Aven have?',
     'single-entity', 'decline', None,
     'qualified item needs compatible subset evidence'),
    ('curated', 'Aven sees 8 red cards. How many red cards does Aven have?',
     'single-entity', 'decline', None,
     'qualified item has no complete compatible total'),
    ('curated',
     'Mira has a budget of $90. Mira spent $15 on a book. '
     'Mira bought a hat. Mira has $20 left from her budget. '
     'How much did Mira pay for the hat?',
     'budget-item-cost', 'number', 55.0,
     '90 dollar budget − 20 remaining − 15 known costs = 5'),
    ('curated', 'Mira bought a hat. How much did Mira pay for the hat?',
     'budget-item-cost', 'decline', None,
     'a residual cost needs one opening and one closing bu'),
    ('curated',
     'Mira has a budget of $90. Mira bought a hat and a book. '
     'Mira has $20 left from her budget. How much did Mira pay for the hat?',
     'budget-item-cost', 'decline', None,
     'the requested item must be the one unknown purchase '),
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
    ('curated',
     'The teacher was 20 years old in 1999. How old was the teacher in 2022?',
     'age-at-year', 'number', 43.0,
     "teacher's dated year age (20 in 1999) projected to 2"),
    ('curated', 'How old was Cato in 2022?',
     'age-at-year', 'decline', None, "no dated year age known for 'cato'"),
    ('curated',
     'Cato was 5 years old in 2000. How old was Cato in 1990?',
     'age-at-year', 'decline', None,
     "projecting 'cato' to 1990 gives a negative age"),
    ('curated',
     'Cato was 20 years old in 1999. Cato was 25 years old in 2001. '
     'How old was Cato in 2022?',
     'age-at-year', 'decline', None,
     "dated age sources for 'cato' disagree at 2022"),
    ('curated',
     'The teacher was 20 years old in 1999. '
     'The child was 10 years old in 2010. How old are they now?',
     'age-at-year', 'decline', None,
     'a deictic dated age ask needs an explicit reference '),
    ('curated',
     'The teacher was 20 years old in 1999. '
     'The child was 10 years old in 2010. '
     'What was their combined age in 2020?',
     'age-at-year', 'number', 61.0,
     "combined dated year age for ['teacher', 'child'] at "),
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
    ('gsm8k',
     'A school has 12 girls. How many of the students are girls?',
     'unique-entity', 'decline', None,
     "the sole holder of 'girl' has no matching 'student' "),
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
    ('curated', 'What percentage of the students enrolled in science courses?',
     'partition-percentage', 'decline', None,
     "resolved partition count is 0 for 'student'/'science"),
    ('curated',
     'In a university with 0 students, 25% enrolled in science courses, '
     '20% of the remaining enrolled in business courses, and the rest enrolled '
     'in humanities courses. What percentage of the students enrolled in '
     'humanities courses?',
     'partition-percentage', 'decline', None,
     "partition total is not positive for 'university'/'st"),
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
    ('gsm8k', 'Calculate the age of Arden and Briar.',
     'single-entity', 'decline', None,
     'a single-dimension ask must name exactly one entity'),
    (
        'gsm8k',
        'Nadia bought 5 new toy cars. Nadia has 40 toy cars now. '
        'How many toy cars did Nadia have originally?',
        'single-entity',
        'decline',
        None,
        'qualified start state has differently qualified even',
    ),
    ('gsm8k', 'How many did Oscar make?',
     'single-entity-elided-measure', 'decline', None, "'oscar' holds 0 measures — an elided-measure ask nee"),
    ('gsm8k', 'How many does Priya have?',
     'single-entity-elided-measure', 'decline', None, "'priya' holds 0 measures — an elided-measure ask nee"),
    ('gsm8k', 'What is the cosine of 0 degrees?',
     'trigonometry', 'number', 1.0, 'trigonometry'),
    ('gsm8k', 'What is the tangent of -90 degrees?',
     'trigonometry', 'decline', None, "'tan' not defined for the given inputs"),
    ('gsm8k',
     'Tom has 3 apples. Bira has 5 apples. Tom sees Zoe. '
     'How many apples do they have combined?',
     'combined', 'decline', None,
     'the collective pronoun has no definitive antecedent '),
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
    # --- the guard-gap closure (session 4). Every row below was found by
    # probing the live matcher, not by reading the consumer: each reaches a
    # guard that had NO probe, from text a real user could type. The probes
    # that COULD NOT be phrased are direct unit tests instead
    # (tests/test_consumer_guard_probes.py + _COVERED_BY_UNIT_TEST below).
    ('gsm8k', 'Callum paid with 20 dollars. How much change did Callum get?',
     'change', 'decline', None, "no resolvable priced-purchase total for 'callum' — a"),
    ('gsm8k', 'What is the slope between (1,1,1) and (2,2,2)?',
     'coordinate', 'decline', None, 'slope is defined for 2-D points'),
    ('gsm8k', 'What is the speed of an object that travels 60 meters and 60 meters in 4 seconds?',
     'physics', 'decline', None, "two 'distance' values stated — 'speed' cannot choose"),
    ('gsm8k', 'Tom has 5 apples. How many more apples does he have than him?',
     'difference', 'decline', None, "a difference ask resolved both sides to 'tom' — a se"),
    ('gsm8k', 'Tom has 3 apples. What is the difference in apples they have?',
     'difference', 'decline', None, 'a pronoun difference ask needs exactly two holders o'),
    ('gsm8k', 'Tom has 3 dollars. Tom has 2 pounds. Mary has 1 dollar. How much more money does Tom have than Mary?',
     'difference', 'decline', None, "measure 'money' is ambiguous across the facts"),
    ('gsm8k', 'Tom has 5 apples. How many did Tom eat?',
     'single-entity-elided-measure', 'decline', None, "no 'eat' events known for 'tom'/'apple'"),
    ('gsm8k', 'Tom found 3 apples. Now Tom has 5 apples. How many does Tom have?',
     'single-entity-elided-measure', 'decline', None, "no quantity known for 'tom' of 'apple' (ask ask/how-"),
    ('gsm8k', 'The bird eats 2 berries per day. How many berries does the bird eat in 3 meters?',
     'rate-span', 'decline', None, "no conversion from 'meter' to the rate's 'day' — can"),
    ('gsm8k', 'Rob earns 10 dollars per hour. How much does Rob earn?',
     'rate-span', 'decline', None, "no unique 'hour' span known for 'rob' to pair with t"),
    ('curated',
     'Nora earns 12 dollars an hour for gardening. '
     'Yesterday she did 50 minutes of tutoring. How much did she earn?',
     'rate-span', 'decline', None,
     "no unique duration for 'nora' doing 'gardening' to p"),
    ('gsm8k', 'A bird eats 2 berries per day. Tom found 3 birds. Now Tom has 5 birds. How many berries does the bird eat in 4 days?',
     'rate-span', 'number', 8, "2.0/day × 4.0 day for 'bird'"),
    ('gsm8k', 'The bird eats 2 berries per day. Tom found 3 birds. Now Tom has 5 birds. How many berries do the birds eat in 4 days?',
     'rate-span', 'decline', None, 'the rate is per-bird'),
    ('gsm8k', 'The bird eats 2 berries per day. How many berries do the birds eat in 4 days?',
     'rate-span', 'decline', None, 'the plural rate subject needs a resolved population'),
    ('gsm8k', 'Birds eat 2 berries per day. How many berries does a bird eat in 4 days?',
     'rate-span', 'decline', None, 'an individual ask cannot use a collective rate'),
    ('gsm8k', 'Birds eat 2 berries per day. Tom has 3 birds. How many berries do the birds eat in 4 days?',
     'rate-span', 'decline', None, 'a collective rate cannot be multiplied by a populati'),
    ('gsm8k', 'Birds eat 2 berries per day. How many days will it take a bird to eat 8 berries?',
     'rate-span-inverse', 'decline', None, 'an individual ask cannot use a collective rate'),
    ('gsm8k', 'A bird eats 2 berries per day. How many days will it take the birds to eat 8 berries?',
     'rate-span-inverse', 'decline', None, 'the plural rate subject needs a resolved population'),
    ('gsm8k', 'The bird eats 2 berries per day. How many berries do the large birds eat in 4 days?',
     'rate-span', 'decline', None, 'the rate subject qualifier needs matching scoped evi'),
    ('gsm8k', "The bird eats 2 berries per day. How many berries does Tom's bird eat in 4 days?",
     'rate-span', 'decline', None, 'the owned rate subject needs matching scoped evidenc'),
    ('gsm8k', 'A bird eats 2 berries per day. Tom has 3 birds. How long does it take the bird to eat 10 berries?',
     'rate-span-inverse', 'decline', None, 'the rate is per-bird — the inverse span ask does not'),
    ('gsm8k', 'The machine makes 5 toys per day. How many years did it take the machine to make 20 toys?',
     'rate-span-inverse', 'decline', None, "no conversion from the rate's 'day' to asked time un"),
    ('gsm8k', 'Tom has 5 dollars. How much money in apples will Tom have left?',
     'money-left', 'decline', None, "asked unit 'apple' does not match resolved measure '"),
    ('gsm8k', 'Tom has 3 dollars. Tom has 2 pounds. How much money does Tom have left?',
     'money-left', 'decline', None, "measure 'currency' is ambiguous across the facts"),
    ('gsm8k', 'Tom has 5 dollars. How much money in apples does Tom have?',
     'single-entity', 'decline', None, "asked unit 'apple' does not match resolved measure '"),
    ('gsm8k', 'Tom has 3 dollars. Tom has 2 pounds. How much money does Tom have?',
     'single-entity', 'decline', None, "measure 'money' is ambiguous across the facts"),
    ('gsm8k', 'Tom found 3 oranges. Now Tom has 4 oranges. Tom has 2 apples. How many more oranges than apples are there?',
     'label-difference', 'decline', None, "missing a total for 'orange' or 'apple'"),
    # reference-lookup ('curated' is the only project loading packs/reference)
    ('curated', 'What is the area of Japan?',
     'reference-lookup', 'number', 377975.0, 'reference'),
    ('curated', 'What is the population of Atlantis in 2020?',
     'reference-lookup', 'decline', None, "no reference fact for the 'population' of 'atlantis'"),
    ('curated', 'What is the population of France?',
     'reference-lookup', 'decline', None, "no reference fact for the 'population' of 'france'"),
    ('curated', 'What is the total population of Europe in 2020?',
     'reference-aggregate', 'number', 543100000.0, 'reference-aggregate'),
    ('curated', 'What is the total population of Narnia in 2020?',
     'reference-aggregate', 'decline', None, "no reference group named 'narnia'"),
    ('curated', 'What is the total population of Europe?',
     'reference-aggregate', 'decline', None, "cannot aggregate the 'population' of 'europe'"),
    ('gsm8k',
     'Cora took 1 hour to finish the task. '
     'How many minutes slower did Cora finish the task than Dax?',
     'completion-duration-difference', 'decline', None,
     'a comparison needs exactly one compatible completion'),
    ('gsm8k',
     'Cora took 1 hour to finish the task. '
     'How many minutes faster did Cora finish the task than Cora?',
     'completion-duration-difference', 'decline', None,
     'a completion-duration comparison needs two distinct '),
    ('gsm8k',
     'Cora took 0 minutes to finish the task. '
     'Dax took 1 hour to finish the task. '
     'How many minutes faster did Cora finish the task than Dax?',
     'completion-duration-difference', 'decline', None,
     'completion durations must be strictly positive'),
    ('gsm8k',
     'Cora took 30 minutes to finish the task. '
     'Dax took 0.5 hours to finish the task. '
     'How many minutes faster did Cora finish the task than Dax?',
     'completion-duration-difference', 'decline', None,
     'equal completion durations do not license faster or '),
    ('gsm8k',
     'Cora took 30 minutes to finish the task. '
     'Dax took 1 hour to finish the task. '
     'How many minutes slower did Cora finish the task than Dax?',
     'completion-duration-difference', 'decline', None,
     "'slower' contradicts the stated completion durations"),
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

_GUARD_FLOOR = 156  # guards WITH a probe: raise as probes are added, never lower
_GAP_CEILING = 0    # guards WITHOUT one: lower as probes are added, never raise

# The denominator is 91, and it was 92 until the boundary bug above was fixed:
# the naive split credited `geometry` with the temporal origo's decline and let
# one branch absorb its neighbour's. Verified against the PRE-refactor file with
# the corrected boundary — also 90 — so the extraction lost nothing; the old
# figure was simply an over-count.

# Guards with no golden probe because they are UNREACHABLE from text by design
# (a defensive re-check, or a slot type that cannot bind the bad value). They
# are covered by direct unit tests on the extracted consumer instead — which is
# only possible once a consumer IS extracted. Listing them here keeps the
# coverage figure honest in both directions: they are not gaps, and they are
# not silently absent either.
_COVERED_BY_UNIT_TEST = {
    ("single-entity", "a qualified subset needs item-level evid"),
    # Each branch is invoked directly by test_budget_defensive_guards.
    ("budget-item-cost", "a residual cost needs one opening and on"),
    ("budget-item-cost", "budget endpoints disagree on participant"),
    ("budget-item-cost", "a later purchase is outside the closed b"),
    ("budget-item-cost", "budget evidence must be asserted rather "),
    ("budget-item-cost", "all costs must belong to the same partic"),
    ("budget-item-cost", "a transaction names a different resource"),
    ("budget-item-cost", "a purchase and payment may describe the "),
    ("budget-item-cost", "an allocation phrase has no unique parti"),
    ("budget-item-cost", "the requested item must be the one unkno"),
    ("budget-item-cost", "the requested item also has a separate s"),
    ("budget-item-cost", "budget amounts must be finite and non-ne"),
    ("budget-item-cost", "a priced purchase needs a nonnegative co"),
    # Account reuse neighbours in test_account_rate_reuse.py exercise these
    # same shared guards through money-left and capacity.
    ("budget-item-cost", "an unpriced purchase leaves the availabl"),
    ("budget-item-cost", "the account ask has an unread condition "),
    ("budget-item-cost", "the stated remainder disagrees with the "),
    ("capacity", "affordability needs one complete unquali"),
    ("capacity", "an account purchase needs a positive fin"),
    ("capacity", "an additional asked budget cannot replac"),
    ("capacity", "the unit price and resource account use "),
    ("money-left", "the requested currency differs from the "),
    ("budget-item-cost", "a stated value lies outside the complete"),
    ("budget-item-cost", "budget evidence repeats a numeric mentio"),
    ("budget-item-cost", "budget events must be actual and affirma"),
    ("budget-item-cost", "an alternative event cannot close a defi"),
    ("budget-item-cost", "a purchase or spending event has no comp"),
    ("budget-item-cost", "an additional resource change is outside"),
    ("budget-item-cost", "known spending and remainder exceed the "),
    # Capacity inquiry/observation facts are emitted with fixed modes and
    # structurally complete fields. Direct malformed stores exercise all seven
    # defensive restatements in tests/test_consumer_guard_probes.py.
    (
        "container-capacity-observation",
        "all-fit evidence establishes a confirmed",
    ),
    ("container-capacity-observation", "capacity arithmetic failed"),
    (
        "container-capacity-observation",
        "capacity needs one compatible fill obser",
    ),
    (
        "container-capacity-observation",
        "capacity needs one compatible inquiry co",
    ),
    (
        "container-capacity-observation",
        "no complete available total for",
    ),
    ("container-capacity-observation", "remainder"),
    (
        "container-capacity-observation",
        "unsupported capacity observation",
    ),
    ("content-progress-remainder-fraction", ""),
    ("content-progress-remainder-fraction", "completed"),
    ("content-progress-remainder-fraction", "completed progress"),
    ("content-progress-remainder-fraction", "measure"),
    ("content-progress-remainder-fraction", "requested remainder fraction"),
    (
        "content-progress-remainder-fraction",
        "the planned progress target needs one de",
    ),
    (
        "content-progress-remainder-fraction",
        "the requested remainder fraction is unre",
    ),
    ("completion-duration-difference", "completion-speed direction"),
    ("molar-mass", "no atomic mass known for"),
    ("molar-mass", "a cost needs a numeric rate"),
    ("molar-mass", "weight needs the gram->kilogram conversi"),
    ("molar-mass", "weight formula failed"),
    # --- session 4: the guard-gap closure. Everything below is probed in
    # tests/test_consumer_guard_probes.py; each entry states WHY text
    # cannot reach it (verified against the matcher, not assumed).
    #
    # The op/value slots are typed or category-gated at the ask, so an
    # unknown op or a non-numeric value never binds:
    ("affine-convert", "a conversion needs a numeric quantity"),
    # both reference asks bind attribute (category-gated) and entity (a name
    # slot) as REQUIRED, and the year template is "{y.value}" off a number
    # slot — an empty attribute/entity or a non-numeric year cannot arrive
    # from text; probed directly in test_consumer_guard_probes.py
    ("reference-lookup", "a reference lookup needs an attribute an"),
    ("reference-lookup", "cannot read"),
    # same structure as reference-lookup: op is a resolves LITERAL, the
    # attribute/group slots are required, the year is "{y.value}" off a
    # number slot — probed directly in test_consumer_guard_probes.py
    ("reference-aggregate", "an aggregate needs an op, an attribute a"),
    ("reference-aggregate", "cannot read"),
    ("arithmetic", "unsupported operation"),
    ("coordinate", "unsupported operation"),
    ("number-theory", "unsupported operation"),
    ("trigonometry", "unsupported operation"),
    ("unit-convert", "a conversion needs a numeric quantity"),
    ("rate-cost", "a rate cost needs a quantity and a rate"),
    ("measure-cost", "unsupported measure operation"),
    ("measure-cost", "unreadable tax rate"),
    ("vector", "unsupported operation"),
    ("physics", "no formula for the"),
    ("list-statistic", "unsupported statistic"),
    # both age-projected asks bind the offset as a REQUIRED counted slot:
    ("age-projected", "projected age ask has no stated year off"),
    # the dated-age ask binds all three required query fields and its target
    # through a number slot. Empty fields and an unreadable target cannot
    # arrive from text; both defensive checks are probed directly.
    ("age-at-year", "a dated age ask needs an entity, measure"),
    ("age-at-year", "cannot read"),
    ("age-at-year", "invalid dated age source for"),
    ("age-at-year", "a dated age group ask needs at least two"),
    ("age-at-year", "is not a current-year age marker"),
    ("age-at-year", "dated"),
    ("age-at-year", "unsupported dated age aggregate"),
    # the stat/vector asks require the numeric list to match at all:
    ("list-statistic", "no numbers to take the"),
    ("vector", "no components to take the"),
    # `currency` is the ONLY interchangeable category, and no ask reaching
    # these two consumers can bind its factless member ('money'):
    ("deficit", "measure"),
    # Contribution-aware deficits opt into the general entity fold. A direct
    # probe supplies one state plus an unsigned event, a store shape no current
    # ask grammar can produce without the document veto firing first.
    ("deficit", "current holdings for"),
    ("unique-entity", "measure"),
    # Exact period-list event totals bind their query fields through required,
    # category-gated slots, and public premise rules emit event rather than
    # state quantities. Direct stores exercise every defensive restatement.
    ("event-period-total", "an event-period total needs two or more "),
    ("event-period-total", "measure"),
    ("event-period-total", "a period activity total requires event e"),
    ("event-period-total", "no direct event evidence for requested p"),
    # the full-read contract is enforced STRUCTURALLY by the matcher —
    # a final span must run to the sentence end and may never swallow a
    # span_blocks word, and every verdict ask anchors `at_start` — so a
    # matched-but-partially-read question cannot occur from text. The
    # consumer guard is the defensive restatement, probed directly:
    ("existential-verdict", "question states"),
    ("logic-disjunction-verdict", "question states"),
    ("logic-verdict", "question states"),
    ("passive-agent-verdict", "question states"),
    ("universal-verdict", "question states"),
    ("verbal-obj-class-verdict", "question states"),
    # `which of them` only routes after resolution has supplied a non-empty
    # group and a day-category marker; full consumption is matcher-enforced.
    # The consumer still defends all three contracts directly.
    ("location-witnesses", "a 'which of them' query needs one exact "),
    ("location-witnesses", "the location witness query needs one dec"),
    ("location-witnesses", "question states"),
    ("location-witnesses", "conflicting direct location evidence for"),
    ("location-witnesses", "observed departure conflicts with the st"),
    # The ask is category-gated to the single explicitly stated population
    # holder, and its premise rule computes every partition within the total.
    # Direct stores probe the consumer's defensive restatement of both facts.
    ("partition-percentage", "partition total needs exactly one holder"),
    ("partition-percentage", "partition value"),
    # Aggregate-measurement asks bind their query fields and the public rules
    # emit ordered, nonnegative, mass-compatible changes. Direct malformed
    # stores exercise every defensive restatement in the consumer.
    ("measurement-reading", "a measurement reading needs a dimension "),
    ("measurement-reading", "the asked dimension"),
    ("measurement-reading", "stated value"),
    ("measurement-reading", "the reading needs one matching placement"),
    ("measurement-reading", "a measured update has no narration order"),
    ("measurement-reading", "an elided measured-content update does n"),
    ("measurement-reading", "the document contains measured changes o"),
    ("measurement-reading", "two aggregate measurement effects have n"),
    ("measurement-reading", "the aggregate measurement anchor is inva"),
    ("measurement-reading", "a measured-content update is invalid"),
    ("measurement-reading", "the scaled dimension"),
    ("measurement-reading", "a total multiplier must be positive"),
    ("measurement-reading", "the added measure"),
    ("measurement-reading", "no known conversion from"),
    ("measurement-reading", "unsupported aggregate operation"),
    # Explicit-unit queries must stay in the anchored dimension; the public
    # grammar excludes the malformed unit, so a direct query probes this.
    ("measurement-reading", "the requested unit has an incompatible d"),
    # Content recovery asks bind both nouns and public rules emit the anchor,
    # placement, and tare shapes. Direct stores probe the defensive restatement
    # and the physically impossible nonpositive remainder.
    ("measurement-reading", "a content amount needs one content and c"),
    ("measurement-reading", "the requested container needs one result"),
    ("measurement-reading", "the content anchor needs one prior conta"),
    ("measurement-reading", "the requested content needs one compatib"),
    ("measurement-reading", "the container tare leaves no positive co"),
    ("measurement-reading", "the requested content has no recoverable"),
    ("measurement-reading", "a measured addition leaves no positive c"),
    ("measurement-reading", "no known"),
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
            m = re.search(r'@consumer\("([a-z-]+)"', body)  # may carry time_scoped=
            if not m:
                continue
            if m.group(1) == "budget-item-cost":
                # Shared guards stay counted after extraction.
                body += (consumers_dir.parent / "account_totals.py").read_text()
            msgs = re.findall(r'"decline",\s*None,\s*\n?\s*f?"([^"]{6,70})', body)
            extracted[m.group(1)] = {x.split("{")[0].split(":")[0].strip()[:40] for x in msgs}

    # ⚠ A BRANCH ENDS at the first non-blank line NOT indented into it — not at
    # the next `if consumer ==`. `answer()` has SHARED code between branches
    # (the temporal origo), and the naive boundary mis-attributes it: geometry
    # was being credited with the origo's decline, and a branch whose successor
    # had been extracted silently absorbed the next one's guards. The same
    # boundary bug that hit the extraction tool, in the measurement.
    lines = text.split("\n")
    blocks = {}
    for i, ln in enumerate(lines):
        m = re.match(r'    if consumer == "([a-z-]+)":', ln)
        if not m:
            continue
        end = next((j for j in range(i + 1, len(lines))
                    if lines[j].strip() and not lines[j].startswith("        ")),
                   len(lines))
        blocks[m.group(1)] = "\n".join(lines[i:end])
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


# --- the temporal-origo split, pinned ---------------------------------------


def test_no_extracted_consumer_silently_loses_the_time_filter():
    """`answer()` resolves the question's reference time PART-WAY DOWN its body
    and rebinds `store` to a time-filtered copy.

    Consumers written above that point never see the filter; those below it
    always do. So a single dispatch before the if-chain is behaviour-preserving
    for the first group and a SILENT REGRESSION for the second — it would drop
    the time scoping, and no corpus item need phrase the difference.

    This pins the two-phase mechanism: every registered consumer is dispatched
    on the side of the origo it was written for.
    """
    import re

    from rulekit.kernel.consumers import CONSUMERS, TIME_SCOPED

    src = (ROOT / "src" / "rulekit" / "kernel" / "answer.py").read_text().split("\n")
    origo = next(i for i, l in enumerate(src) if "THE TEMPORAL ORIGO" in l)
    phase1 = next(i for i, l in enumerate(src) if "Phase 1: consumers that lived ABOVE" in l)
    phase2 = next(i for i, l in enumerate(src) if "Phase 2: consumers that lived BELOW" in l)

    assert phase1 < origo < phase2, (
        "the two dispatch points must straddle the origo, or the flag means nothing"
    )
    # a consumer still in the if-chain BELOW the origo must not also be
    # registered without the flag
    for i, line in enumerate(src):
        m = re.match(r'    if consumer == "([a-z-]+)":', line)
        if m and i > origo and m.group(1) in CONSUMERS:
            assert m.group(1) in TIME_SCOPED, (
                f"{m.group(1)} lives below the origo but is dispatched early"
            )


def test_the_origo_still_runs_for_chain_consumers():
    """The shared time scoping must not have been swallowed into a consumer
    module — a boundary drawn to "the next `if consumer ==`" would have moved
    it, since it sits between two branches."""
    answer_src = (ROOT / "src" / "rulekit" / "kernel" / "answer.py").read_text()
    assert "THE TEMPORAL ORIGO" in answer_src
    assert "_question_reference_time" in answer_src

    # look for the CODE, not the prose: `consumers/__init__.py` documents the
    # origo at length, and a check that a comment is absent would forbid
    # explaining the very trap it guards
    consumers = ROOT / "src" / "rulekit" / "kernel" / "consumers"
    for mod in consumers.glob("*.py"):
        body = mod.read_text()
        assert "_question_reference_time(" not in body, (
            f"{mod.name} swallowed the shared temporal origo"
        )
