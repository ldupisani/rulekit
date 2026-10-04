# Mixture composition and processes in curated

One infrastructure handles aqueous and nonaqueous samples. It retains sample
identity, measurement basis and process evidence independently of material
vocabulary. All examples below are invented; every construction loads through
`projects/curated` without benchmark-only packs.

## Composition questions

| Example | Result |
| --- | --- |
| Nora has 5 kilograms of alloy. The alloy contains 12% tin by mass. How many grams of tin are in the alloy? | 600 grams |
| Nora has 750 grams of cereal. The cereal is 20% raisins by mass. How many grams of raisins are in the cereal? | 150 grams |
| Nora has 2 kilograms of oil blend. The oil blend contains 15% sunflower oil by mass. How much sunflower oil is in the oil blend? | 0.3 kilograms |
| Nora has 10 moles of gas mixture. The gas mixture is 30% helium by moles. How many moles of helium are in the gas mixture? | 3 moles |
| Nora collects 3 liters of brine. The brine is 20% salt by volume. How many ml of salt are in the brine? | 600 ml under the elementary volume convention |

The same composition can be expressed as “is 20% salt,” “contains 20 percent
salt,” “has 20% salt,” “has 20% salt content,” “has a salt content of 20%,”
“the salt content of the brine is 20%,” or “20% of the brine is salt.” A
trailing “by mass,” “by weight,” “by volume,” or “by moles” retains the basis
in the evidence. These are alternatives for stating a proportion, not
separate arithmetic solvers.

Sample forms include “Nora has/collects/obtained …,” “a tank contains …,”
“the alloy weighs …,” and a relative clause such as “a tank contains 5
kilograms of alloy which is 12% tin by mass.” An explicitly named composition
may precede its sample measurement. A solvent alias such as “the water” needs
an earlier, uniquely identified sample.

Question forms include “how many grams of raisins are in the cereal,” “how
much resin is in the solution,” “what mass of tin is in the alloy,” “how many
grams of salt remain in the brine,” and “what percentage of the alloy is
tin?” An omitted output unit uses the sample unit. “What volume” cannot
silently request a mass result, and explicit percentage bases must agree
with the measured quantity. No density or molar-mass conversion is inferred.

Unqualified percentages retain an empty basis and use the existing elementary
same-dimension convention, which the answer explanation names. This preserves
the original seawater questions; it is not a scientific determination of the
volume occupied by recovered solid salt. Explicit basis information always
takes precedence. The current volume convention likewise does not model
contraction or distinguish every laboratory definition of concentration.

## Count-based mixtures

“The bead mixture contains 100 beads. The bead mixture contains 20% glass
beads by count. How many glass beads are in the bead mixture?” returns **20**.
Count is a separate basis: a mass fraction cannot answer a count question.
Samples, components and every supported process must preserve whole counts.

## Distinct samples and blending

> A bucket contains 2 kilograms of brine. A tank contains 3 kilograms of brine.
> The brine in the bucket is 10% salt by mass. The brine in the tank is 20%
> salt by mass. Nora mixes the brine in the bucket with the brine in the tank.
> What percentage of the mixture is salt?

Result: **16%**, from 0.2 + 0.6 kilograms of salt in 5 kilograms total.
“Combines … with …” and “the brine … is mixed with …” use the same operation.
Labeled containers such as tank A and tank B also retain distinct identities.
Missing or ambiguous holder references decline. Combining samples does not
invent a destination container or establish uniform mixing.

The ledger supports mass and mole-amount addition directly. Volume addition
requires the explicit premise **“Volumes are additive.”** Without that premise,
volume blending and dilution decline. This is a stated modeling assumption,
not a property inferred from the materials' names.

## Ordered changes

Start with: “Nora has 2 kilograms of brine. The brine contains 20% salt by mass.”

| Further evidence and question | Result |
| --- | --- |
| Nora adds 2 kilograms of pure water to the brine. What percentage of the brine is salt? | 10% |
| Nora added 500 grams of pure salt to the brine. What percentage of the brine is salt? | 36% |
| The brine is homogeneous. Nora removes 1 kilogram of brine. How many grams of salt remain in the brine? | 200 grams |
| Nora removes 1 kilogram of water from the brine without losing salt. What percentage of the brine is salt? | 40% |

“Uniform” is an alternative to “homogeneous.” Proportional withdrawal requires
that evidence. An addition or combination clears uniformity until it is
established again. Addition requires an explicitly pure component. Selective
removal requires an identified solvent and explicit retention of the requested
component. Updates are applied in sentence order after initial measurements
and compositions; unsupported or interleaved remeasurement declines.

## Recovery in different solvents

> Nora has 200 grams of resin solution in ethanol. The resin solution is 15%
> resin by mass. How many grams of resin will be left after all the ethanol
> is removed without losing resin?

Result: **30 grams**. The solvent belongs to this sample, and the question
explicitly establishes retention. Alternatives include “how much … will
remain,” “what mass … will Nora get,” “when” for “after,” and “without losing
any resin.” Removal can instead be a preceding statement: “Nora removes all
ethanol from the resin solution without losing resin.”

Existing aqueous evaporation asks remain available, including “the water has
completely evaporated.” Their declared retention category is scoped to that
aqueous evaporation process. Nonaqueous evaporation does not inherit this rule.
Complete solvent removal preserves the stated component amount but leaves the
total residue unknown, since other components may remain. A subsequent residue
percentage therefore declines without further evidence.

## Shared representation and boundaries

`MixtureEvidence` holds measured samples, component shares and ordered process
events. Structural references retain holder labels and descriptions instead
of reducing them to a common noun. The consumer checks dimensions, unique
sample/composition association, every numeric mention, process order and all
mixture evidence. It reuses the conversion registry and arithmetic log.
Vocabulary, material categories, basis words and the scoped aqueous retention
category live in YAML.

Current support tracks one requested component per sample. Multiple stated
component shares, unbound or conflicting samples, unaccounted narration,
negative or excessive withdrawals, incompatible bases, unspecified recovery,
negated or ongoing removal, and unknown total amounts decline. The engine
does not infer densities, reactions, complementary compositions, arbitrary
compound-name synonyms, sample homogeneity or gas pressure/temperature laws.
Laboratory concentration units such as grams per liter are not implemented
by these rules.

`tests/test_general_mixtures.py` exercises materials × composition phrasings ×
question phrasings, explicit bases, unit conversions, labeled samples,
blending, dilution, withdrawal, retention, precision boundaries and generated
premise round trips. `tests/test_mixture_component.py` and
`tests/test_mixture_paraphrases.py` preserve the earlier curated and GSM8K
behavior. These are synthetic construction tests, not claims of independent
benchmark generalization.

Validation for the generalized implementation: 824 focused mixture checks
passed, followed by a 202-test rerun of the generalized family including its
additional result-identity boundary. Curated stayed 71/71. GSM8K DEV-train,
DEV-holdout and ASDiv DEV comparisons each had zero regressions and zero new
wrong answers. Curated/GSM8K lint had zero errors and only their existing
warnings. The broad synthetic run had 10,062 passes and one seeded-generation
expectation failure; the generated scenario was inspected, the expectation
was corrected, and its four-test file passed. This is a broad run plus focused
final reruns, not a claim of an uninterrupted full-suite pass on the final edit.
