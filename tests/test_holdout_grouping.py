"""The internal dev-train/dev-holdout cut buckets by GROUP when a dataset
declares one (schemas.DatasetDef.group), and stays byte-identical when none is
declared.

Why this exists (synthetic — never a corpus string): FOLIO items share premise
blocks (many conclusions per story). `holdout_bucket(item.text)` puts one
story's conclusions on BOTH sides of the internal cut, so dev-holdout stops
being a tuning-overfit proxy — the story was already visible from dev-train.
With `group`, items sharing the key land on one side, like the DEV/TEST cut.
"""
from rulekit.harness.firewall import BenchItem, holdout_bucket, slice_items


def _item(text: str, group: str | None = None) -> BenchItem:
    return BenchItem(id=text[:12], text=text, expect=1.0, group=group)


def test_grouped_items_never_straddle_the_cut():
    # many items per group, texts chosen arbitrarily — the invariant must hold
    # for ANY texts, which per-item hashing does not guarantee
    train = [
        _item(f"story {s} conclusion {c}", group=f"story-{s}")
        for s in range(20)
        for c in range(3)
    ]
    tr = slice_items(train, [], "dev-train")
    ho = slice_items(train, [], "dev-holdout")
    assert {i.group for i in tr} & {i.group for i in ho} == set()
    assert len(tr) + len(ho) == len(train)
    # every item of a group is on the side its group hashes to
    for i in tr + ho:
        assert holdout_bucket(i.group) == ("dev-train" if i in tr else "dev-holdout")


def test_ungrouped_cut_is_unchanged():
    # group=None (every pre-existing project) must bucket on the item text,
    # byte-identical to the behavior before the field existed
    train = [_item(f"question number {n}") for n in range(40)]
    tr = slice_items(train, [], "dev-train")
    ho = slice_items(train, [], "dev-holdout")
    assert [i.text for i in tr] == [
        i.text for i in train if holdout_bucket(i.text) == "dev-train"
    ]
    assert [i.text for i in ho] == [
        i.text for i in train if holdout_bucket(i.text) == "dev-holdout"
    ]


def test_group_does_not_change_item_identity():
    # the group key influences WHICH side an item lands on, never its id/text
    a = _item("same text", group="g1")
    b = _item("same text", group=None)
    assert a.id == b.id and a.text == b.text
