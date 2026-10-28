"""Early category filtering preserves the qualified generation domain."""
import json
import pytest
from rulekit.data.project import load_project
from rulekit.generation.sample import _qualified_fillers, _counted_qualified_fillers


@pytest.fixture
def registry(tmp_path):
    pack = tmp_path / 'pack'
    pack.mkdir()
    docs = {
        tmp_path / 'project.yaml': {'format':'rulekit/project@1', 'name':'domain-filter', 'packs':['./pack']},
        pack / 'pack.yaml': {'format':'rulekit/pack@1', 'name':'invented', 'version':'0.1.0'},
        pack / 'lexicon.yaml': {'format':'rulekit/lexicon@1', 'entries': {
            'red': {'senses':['adjective']}, 'blue': {'senses':['adjective']},
            'large': {'senses':['adjective']},
            'box': {'senses':['noun'], 'plural':'boxes'}, 'ball': {'senses':['noun'], 'plural':'balls'},
            'one': {'senses':['number']}, 'two': {'senses':['number']}}},
        pack / 'numbers.yaml': {'format':'rulekit/numbers@1', 'numbers':{'one':1, 'two':2}},
        pack / 'categories.yaml': {'format':'rulekit/categories@1',
            'categories': {'color':{'parent':'adjective'}, 'size':{'parent':'adjective'},
                           'container':{'parent':'noun'}, 'toy':{'parent':'noun'}},
            'members': {'color':['red', 'blue'], 'size':['large'], 'container':['box'], 'toy':['ball']},
            'attribute_compatibility': {'color':['container','toy'], 'size':['container']}},
    }
    for path, doc in docs.items():
        path.write_text(json.dumps(doc))
    return load_project(tmp_path).registry


@pytest.mark.parametrize('head', [None, 'container', 'toy'])
@pytest.mark.parametrize('modifier', [None, 'color', 'size'])
@pytest.mark.parametrize('generate', [_qualified_fillers, _counted_qualified_fillers])
def test_filtered_domains_retain_membership_and_order(registry, head, modifier, generate):
    old = [f for f in generate(registry)
           if (head is None or registry.word_in_category(f.identity, head))
           and (modifier is None or registry.word_in_category(f.qualifier, modifier))]
    assert generate(registry, head_category=head, modifier_category=modifier) == old


@pytest.mark.parametrize('head, category', [('box', 'container'), ('ball', 'toy')])
def test_modifier_category_checks_every_retained_qualifier(registry, head, category):
    from rulekit.data.schemas import MatchToken
    from rulekit.kernel.model import Unit
    from rulekit.kernel.patterns import _slot_ok

    token = MatchToken(slot='item', cat=category, qualified=True, qualifier_cat='color',
                       all_qualifiers=True)
    features = {'senses': ['noun'], 'lemma': head, 'fold': head, 'qualifier': 'red'}
    # Legacy one-modifier units and the structured representation agree.
    assert _slot_ok(Unit(0, (), features), token, registry)
    assert _slot_ok(Unit(0, (), {**features, 'reference_qualifiers': ('red',)}), token, registry)
    assert _slot_ok(Unit(0, (), {**features, 'reference_qualifiers': ('blue', 'red')}), token, registry)
    # The outer accepted modifier must not erase a different inner constraint.
    assert not _slot_ok(Unit(0, (), {**features, 'reference_qualifiers': ('large', 'red')}),
                        token, registry)
    legacy = token.model_copy(update={'all_qualifiers': False})
    assert _slot_ok(Unit(0, (), {**features, 'reference_qualifiers': ('large', 'red')}),
                    legacy, registry)


def test_complete_qualifier_check_requires_a_declared_category():
    from pydantic import ValidationError
    from rulekit.data.schemas import MatchToken

    with pytest.raises(ValidationError, match='requires `qualifier_cat`'):
        MatchToken(slot='item', type='qualified', all_qualifiers=True)
