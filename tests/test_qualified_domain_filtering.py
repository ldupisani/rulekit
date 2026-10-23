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
            'red': {'senses':['adjective']}, 'large': {'senses':['adjective']},
            'box': {'senses':['noun'], 'plural':'boxes'}, 'ball': {'senses':['noun'], 'plural':'balls'},
            'one': {'senses':['number']}, 'two': {'senses':['number']}}},
        pack / 'numbers.yaml': {'format':'rulekit/numbers@1', 'numbers':{'one':1, 'two':2}},
        pack / 'categories.yaml': {'format':'rulekit/categories@1',
            'categories': {'color':{'parent':'adjective'}, 'size':{'parent':'adjective'},
                           'container':{'parent':'noun'}, 'toy':{'parent':'noun'}},
            'members': {'color':['red'], 'size':['large'], 'container':['box'], 'toy':['ball']},
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
