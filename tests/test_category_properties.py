"""Typed category properties share inheritance without inventing measurements."""
from dataclasses import replace
from pathlib import Path

import pytest

from rulekit.data.packs import LoadedPack
from rulekit.data.project import load_project
from rulekit.data.registry import CompileError, compile_registry
from rulekit.data.schemas import CategoriesDoc, ConversionsDoc, LexiconEntry, PackDoc
from rulekit.data.properties import PropertyError
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.properties import Measurement, evaluate_property
from rulekit.kernel.engine import solve


def make_registry(categories, members=None, attrs=None, formulas=None, bindings=None,
                  units=None, conversions=None):
    words = {'animal', 'pet', 'mammal', 'bird', 'bear', 'whale', 'widget', 'damaged', 'meter', 'centimeter'}
    words.update(w for values in (members or {}).values() for w in values)
    words.update(attrs or {})
    return compile_registry([LoadedPack(
        name='properties', root=Path('/tmp/rulekit-property-fixture'),
        manifest=PackDoc(format='rulekit/pack@1', name='properties'),
        lexicon={word: LexiconEntry(senses=['noun'], plural=word+'s') for word in words},
        categories=[CategoriesDoc(format='rulekit/categories@1', categories=categories,
            members=members or {}, attrs=attrs or {}, formulas=formulas or {},
            parameter_bindings=bindings or {}, formula_units=units or {'length':'meter'})],
        conversions=[ConversionsDoc(format='rulekit/conversions@1', conversions=conversions or [])],
        fingerprint='properties')])


def area():
    return {'inputs':{'length':'length', 'width':'length'}, 'expr':'length * width',
            'result_dimension':{'length':2}}


def test_categories_supply_defaults_without_propagating_them_upward_or_sideways():
    r=make_registry({
        'animal':{'parent':'noun'},
        'mammal':{'parent':'animal'},
        'quadruped':{'parent':'animal','attrs':{'legs':4}},
        'damaged':{'parent':'quadruped','attrs':{'legs':3}},
        'participants':{'parent':'noun','includes':['animal']},
    }, {'quadruped':['bear'],'mammal':['whale'],'damaged':['widget']})
    assert r.attribute_value('bear','legs') == r.attribute_value('bears','legs') == 4
    assert r.attribute_value('widget','legs') == 3
    for term in ('animal','mammal','whale','participants'):
        assert r.attribute_value(term,'legs') is None


def test_explicit_word_override_resolves_inherited_defaults_for_both_forms():
    r=make_registry({'family':{'parent':'noun','attrs':{'capacity':8}}},
                    {'family':['widget']}, {'widget':{'capacity':6}})
    assert r.attribute_value('widget','capacity') == r.attribute_value('widgets','capacity') == 6
    assert r.property_sources[('widgets','capacity')][0].kind == 'word'


def test_unrelated_conflicting_defaults_require_an_explicit_resolution():
    categories={'a':{'parent':'noun','attrs':{'capacity':6}},
                'b':{'parent':'noun','attrs':{'capacity':8}}}
    members={'a':['widget'],'b':['widget']}
    with pytest.raises(CompileError,match='conflicting property'):
        make_registry(categories,members)
    r=make_registry(categories,members,{'widget':{'capacity':7}})
    assert r.attribute_value('widget','capacity') == 7


def test_equal_defaults_have_all_sources_and_are_order_independent():
    categories={'a':{'parent':'noun','attrs':{'capacity':6}},
                'b':{'parent':'noun','attrs':{'capacity':6}}}
    r=make_registry(categories,{'a':['widget'],'b':['widget']})
    assert r.attribute_value('widget','capacity') == 6
    assert {s.owner for s in r.property_sources[('widget','capacity')]} == {'a','b'}


@pytest.mark.parametrize('definition',[
    {'inputs':{'x':'length','y':'time'},'expr':'x + y','result_dimension':'length'},
    {'inputs':{'x':'length'},'expr':'x*x','result_dimension':'length'},
    {'inputs':{'x':'length'},'expr':'missing*x','result_dimension':'length'},
    {'inputs':{'x':'length','y':'length'},'expr':'x','result_dimension':'length'},
    {'inputs':{'x':'length'},'expr':'x.__class__','result_dimension':'length'},
])
def test_invalid_formula_contracts_fail_at_compile_time(definition):
    with pytest.raises(CompileError):
        make_registry({'family':{'parent':'noun','formulas':{'area':definition}}})


def test_derived_property_and_parameter_cycles_fail_even_before_a_word_is_added():
    formula={'inputs':{'other':{}},'expr':'other','result_dimension':{}}
    with pytest.raises(CompileError,match='dependency cycle'):
        make_registry({'family':{'parent':'noun','formulas':{
            'first':formula,'other':{'inputs':{'first':{}},'expr':'first','result_dimension':{}}}}})
    with pytest.raises(CompileError,match='binding cycle'):
        make_registry({'family':{'parent':'noun','formulas':{'area':area()},
            'parameter_bindings':{'length':'width','width':'length'}}})


def test_parameter_equalities_are_explicit_and_do_not_apply_to_parent_classes():
    r=make_registry({
        'rectangle':{'parent':'noun','formulas':{'area':area()}},
        'equal_sides':{'parent':'rectangle','parameter_bindings':{'length':'side','width':'side'}},
    },{'rectangle':['widget'],'equal_sides':['pet']})
    assert evaluate_property(r,'pet','area',{'side':7}).value == 49
    with pytest.raises(PropertyError,match='unrecognized'):
        evaluate_property(r,'widget','area',{'side':7})
    with pytest.raises(PropertyError,match='contradict'):
        evaluate_property(r,'pet','area',{'length':7,'width':6})


def test_word_parameter_bindings_keep_their_own_sources():
    r=make_registry({},formulas={'widget':{'area':area()}},
                    bindings={'widget':{'length':'side','width':'side'}})
    assert evaluate_property(r,'widget','area',{'side':7}).value==49
    assert r.property_sources[('widget','binding:length')][0].owner=='widget'
    with pytest.raises(CompileError,match='both scalar and derived'):
        make_registry({},attrs={'widget':{'area':7}},formulas={'widget':{'area':area()}})


def test_non_geometry_properties_reuse_scalars_dependencies_and_dimensional_checks():
    r=make_registry({'package':{'parent':'noun','attrs':{'capacity':6},'formulas':{
        'contents':{'inputs':{'packages':{},'capacity':{}},'expr':'packages * capacity','result_dimension':{}},
        'cost':{'inputs':{'contents':{},'price':'money'},'expr':'contents * price','result_dimension':'money'},
    }}},{'package':['widget']})
    log=ArithmeticLog()
    result=evaluate_property(r,'widgets','cost',{'packages':4,'price':2},log)
    assert result.value == 48
    assert result.dimension == (('money',1.0),)
    assert len(log.entries)==2
    with pytest.raises(PropertyError,match='consume all'):
        evaluate_property(r,'widget','contents',{'packages':4,'price':2})


@pytest.fixture(scope='module')
def project():
    return load_project(Path('projects/curated'))


def test_shape_spatial_dimension_is_distinct_from_result_dimension(project):
    r=project.registry
    assert r.attribute_value('circle','spatial_dimension') == 2
    assert r.attribute_value('sphere','spatial_dimension') == 3
    assert r.derived_attribute('sphere','surface area').result_dimension == (('length',2),)
    assert r.derived_attribute('sphere','volume').result_dimension == (('length',3),)
    assert r.derived_attribute('circle','volume') is None
    assert r.attribute_value('geometry_shape','spatial_dimension') is None


def test_unit_scaling_respects_area_and_volume_powers(project):
    r=project.registry
    result=evaluate_property(r,'rectangle','area',{'length':Measurement(2,'meter'),
        'width':Measurement(30,'centimeter')}, output_unit='centimeter')
    assert result.value == pytest.approx(6000)
    assert evaluate_property(r,'cube','volume',{'side':Measurement(2,'meter')},
                            output_unit='centimeter').value == pytest.approx(8_000_000)
    with pytest.raises(PropertyError,match='incompatible'):
        evaluate_property(r,'circle','area',{'radius':Measurement(3,'kilogram')})


def test_unit_conversion_stays_within_the_declared_family_at_every_hop():
    r=make_registry({
        'mass_family':{'parent':'noun'},
        'volume_family':{'parent':'noun'},
        'package':{'parent':'noun','formulas':{'load':{
            'inputs':{'amount':'mass'},'expr':'amount','result_dimension':'mass'}}},
    }, {'mass_family':['massunit','massmiddle','masssmall','ambiguous','isolated'],
        'volume_family':['volumeunit','ambiguous'], 'package':['widget']},
        units={'mass':{'unit':'massunit','category':'mass_family'}}, conversions=[
            {'from':'masssmall','to':'massmiddle','factor':2},
            {'from':'massmiddle','to':'massunit','factor':3},
            {'from':'massunit','to':'ambiguous','factor':10},
            {'from':'ambiguous','to':'volumeunit','factor':4},
            {'from':'isolated','to':'volumeunit','factor':5},
        ])
    assert evaluate_property(r,'widget','load',{'amount':Measurement(5,'masssmall')}).value==30
    assert evaluate_property(r,'widget','load',{'amount':30},output_unit='masssmall').value==5
    for unit in ('volumeunit','isolated'):
        with pytest.raises(PropertyError,match='incompatible'):
            evaluate_property(r,'widget','load',{'amount':Measurement(5,unit)})
        with pytest.raises(PropertyError,match='incompatible'):
            evaluate_property(r,'widget','load',{'amount':5},output_unit=unit)
    legacy=replace(r,formula_unit_categories={})
    with pytest.raises(PropertyError,match='incompatible'):
        evaluate_property(legacy,'widget','load',{'amount':Measurement(5,'masssmall')})
    assert evaluate_property(legacy,'widget','load',{'amount':Measurement(5,'massmiddle')}).value==15


@pytest.mark.parametrize('family',['unknown','volume_family'])
def test_formula_unit_contract_requires_a_declared_matching_family(family):
    with pytest.raises(CompileError,match='noun unit family'):
        make_registry({'volume_family':{'parent':'noun'}},
                      units={'length':{'unit':'meter','category':family}})


def test_lexical_ordinals_do_not_leak_through_noun_plural_morphology(project):
    assert project.registry.attribute_value('second','ordinal_index') == 2
    assert project.registry.attribute_value('seconds','ordinal_index') is None
    assert project.registry.attribute_value('squares','measurement_power') is None


def test_attribute_and_formula_sources_point_to_editable_yaml(project):
    r=project.registry
    for term,key in [('cat','legs'),('square','area'),('cube','volume')]:
        origins=r.property_sources[(term,key)]
        assert origins
        for origin in origins:
            ref=project.source_index.properties[(origin.kind,origin.owner,key)]
            assert ref.path.exists()
            assert ref.line>0
    for loaded in (project,load_project(Path('projects/gsm8k'))):
        for pack in loaded.packs:
            for doc in pack.geometry:
                for formula in doc.formulas:
                    assert loaded.registry.derived_attribute(formula.shape,formula.quantity) is None, (
                        'shipped typed properties must not be copied into the legacy table')


@pytest.mark.parametrize('text,value',[
    ('What is the area of a circle with radius 7?',153.94),
    ('Calculate the area of a rectangle with length 7 and width 3.',21),
    ('What is the area of a triangle with base 7 and height 4?',14),
    ('What is the perimeter of a square with side 7?',28),
    ('What is the volume of a cube with side 17?',4913),
    ('What is the volume of a cylinder with radius 3 and height 5?',141.37),
    ('What is the volume of a cuboid with length 3 and width 4 and height 5?',60),
    ('What is the surface area of a sphere with radius 3?',113.1),
    ('What is the base area of a cylinder with radius 3?',28.27),
    ('What is the area of a rectangle with 7 length and 3 width?',21),
    ('What is the area of a rectangle with length 2 meters and width 30 centimeters in square centimeters?',6000),
    ('What is the volume of a cube with side 2 meters in cubic centimeters?',8_000_000),
])
def test_geometry_properties_work_in_curated_with_alternate_grammar(project,text,value):
    result=solve(text,project.registry)
    assert result.value == pytest.approx(value),result.answer
    assert result.deficiencies() == []
    assert result.answer.proof


@pytest.mark.parametrize('text',[
    'What is the volume of a circle with radius 4?',
    'What is the area of a circle with length 4?',
    'What is the area of a rectangle with length 4?',
    'What is the area of a rectangle with side 4?',
    'What is the area of a square with length 4 and width 5?',
    'What is the area of a cylinder with radius 4 and height 5?',
    'What is the cross-sectional area of a sphere with radius 4?',
    'What is the area of a rectangle with length 4 and length 4?',
    'What is the area of a circle with radius 4 and height 5?',
    'What is the area of a rectangle with length 4 meters and width 5?',
    'What is the area of a circle with radius 4 kilograms?',
    'What is the area of a circle with radius 4 meters in cubic centimeters?',
])
def test_geometry_declines_missing_conflicting_or_ambiguous_measurements(project,text):
    result=solve(text,project.registry)
    assert not result.answer.committed,result.answer


@pytest.mark.parametrize('ask_id',[
    'ask/geometry-formula','ask/geometry-formula-value-first','ask/geometry-formula-measured',
    'ask/compute-shape-property','ask/compute-shape-property-value-first','ask/compute-shape-property-measured',
])
@pytest.mark.parametrize('shape,quantity,source',[
    ('rectangle','area','rectangle_geometry'),
    ('cube','volume','uniform_section_solid'),
    ('sphere','surface area','sphere_geometry'),
])
def test_generation_reuses_property_contracts_and_produces_answerable_questions(project,ask_id,shape,quantity,source):
    from rulekit.generation.ask_generation import generate_ask_scenario
    candidate=generate_ask_scenario(project,ask_id=ask_id,seed=23,
        locked_bindings={'shape':shape,'quantity':quantity})
    assert candidate.answer['kind']=='number',candidate
    result=solve(candidate.question,project.registry)
    assert result.answer.committed
    assert result.deficiencies()==[]
    assert source in result.answer.proof.steps[0].detail


@pytest.mark.parametrize('term,attribute,value',[
    ('bears','legs',4),('crows','legs',2),('butterflies','legs',6),
    ('frogs','legs',4),('cars','wheels',4),('bicycles','wheels',2),('boats','wheels',0),
])
def test_shared_anatomy_and_vehicle_defaults(project,term,attribute,value):
    assert project.registry.attribute_value(term,attribute)==value
    assert project.registry.attribute_sources(term,attribute)


@pytest.mark.parametrize('question,reason',[
    ('What is the area of a rectangle with length 4 and length 4?', 'each geometry parameter must be stated once'),
    ('What is the area of a circle with radius -4?', 'geometry measurements must be finite and nonnegative'),
    ('What is the area of a circle with radius 4 meters in cubic centimeters?', 'requested geometry units must match'),
])
def test_geometry_boundary_reaches_the_intended_guard(project,question,reason):
    result=solve(question,project.registry)
    assert result.answer.kind=='decline'
    assert result.answer.reason.startswith(reason)
