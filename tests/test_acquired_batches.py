"""Invented acquisitions with batch-local selection, classification and disposal."""
from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import BatchEvidence

@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry

FIRST = [
    "After downloading 300 files, Nora deleted 60% of them because they were not helpful.",
    "Nora downloaded 300 files and deleted 3/5 of them because they were irrelevant.",
    "Nora downloaded 300 files. She deleted 60% of them because they were useless.",
]
SECOND = [
    "She downloaded 200 more files but again realized that 3/4 of them were irrelevant.",
    "She downloaded 200 files and realized that 75% of them were not useful.",
    "She downloaded 200 more files. She realized that three fourths of them were unrelated.",
]
ASKS = [
    "How many valuable files was Nora left with after deleting the unrelated files she downloaded in the second round?",
    "How many useful files does Nora have left after deleting the irrelevant files?",
    "How many relevant files remain after deleting the unhelpful files?",
    "How many files remain after deleting the irrelevant files?",
]
@pytest.mark.parametrize("first",FIRST)
@pytest.mark.parametrize("second",SECOND)
@pytest.mark.parametrize("ask",ASKS)
def test_batch_local_complements_and_question_completion(reg,first,second,ask):
    result=solve(f"{first} {second} {ask}",reg)
    assert result.answer.value == 170, result.answer
    assert result.answer.proof
    assert len(result.store.by_kind(BatchEvidence)) >= 2

@pytest.mark.parametrize("acquire",["downloaded","collected","received"])
@pytest.mark.parametrize("item",["files","documents","images","photos","photographs"])
@pytest.mark.parametrize("dispose",["deleted","discarded","rejected"])
def test_reusable_acquisitions_and_disposals(reg,acquire,item,dispose):
    result=solve(f"Nora {acquire} 300 {item} and {dispose} 60% of them. "
                 f"She {acquire} 200 more {item} and {dispose} three fourths of them. "
                 f"How many {item} does Nora have left?",reg)
    assert result.answer.value == 170, result.answer

@pytest.mark.parametrize("ask,expected",[
    ("How many files remain?",320),
    ("How many useful files remain?",170),
    ("How many irrelevant files remain?",150),
    ("How many useful files remain after deleting the helpful files?",120),
    ("How many files remain after deleting the helpful files?",270),
])
def test_classification_is_not_removal(reg,ask,expected):
    result=solve(f"{FIRST[1]} {SECOND[0]} {ask}",reg)
    assert result.answer.value == expected, result.answer

@pytest.mark.parametrize("ask,expected",[
    ("How many files did Nora delete?",330),
    ("How many irrelevant files did Nora delete?",330),
    ("How many helpful files did Nora delete?",0),
    ("How many useful files remain?",170),
])
def test_disposed_and_retained_quality(reg,ask,expected):
    result=solve(f"{FIRST[1]} She downloaded 200 files and deleted 75% of them because they were unrelated. {ask}",reg)
    assert result.answer.value == expected, result.answer

@pytest.mark.parametrize("change",[
    {"first":"Nora downloaded 301 files and deleted 60% of them."},
    {"first":"Nora downloaded 300 files and deleted 160% of them."},
    {"first":"Nora downloaded 300 files and did not delete 60% of them."},
    {"first":"Nora downloaded 300 files and tried to delete 60% of them."},
    {"first":"Nora will download 300 files and delete 60% of them."},
    {"first":"Nora downloaded 300 files and deleted 60% of them. She lost 5 files."},
    {"first":"Nora downloaded 300 red files and deleted 60% of them."},
    {"second":"Tova downloaded 200 files and realized that 75% of them were irrelevant."},
    {"second":"She downloaded 200 documents and realized that 75% of them were irrelevant."},
    {"second":"She downloaded 200 files."},
    {"second":"She downloaded 200 files and realized that 75% of all files were irrelevant."},
    {"ask":"How many files remain after deleting the irrelevant documents?"},
    {"ask":"How many files was Tova left with after deleting the irrelevant files?"},
    {"ask":"How many files remain after deleting the irrelevant files she downloaded in the third round?"},
    {"ask":"How many files remain after deleting the irrelevant files she downloaded in the first round?"},
    {"ask":"How many files remain after deleting the irrelevant files she collected in the second round?"},
    {"ask":"How many files remain after deleting the irrelevant files Tova downloaded in the second round?"},
    {"ask":"How many files remain tomorrow?"},
])
def test_scope_and_incomplete_evidence_decline(reg,change):
    parts=dict(first=FIRST[1],second=SECOND[0],ask=ASKS[0]);parts.update(change)
    result=solve(" ".join(parts.values()),reg)
    assert not result.answer.committed, result.answer


def test_three_equal_sized_batches_keep_distinct_identity(reg):
    result=solve("Nora collected 120 documents and discarded half of them. "
                 "She collected 120 documents and discarded one third of them. "
                 "She collected 120 documents and discarded one fourth of them. "
                 "How many documents remain?",reg)
    assert result.answer.value == 230, result.answer

@pytest.mark.parametrize("rule",[
    "arithmetic/acquired-batch-counted-discard", "arithmetic/acquired-batch-counted-discard-reason",
    "arithmetic/acquired-batch-counted-discard-negative-reason", "arithmetic/acquired-batch-counted-classify",
    "arithmetic/acquired-batch-more-classify-negative", "arithmetic/after-acquisition-discard-negative-reason",
    "arithmetic/acquired-batch-counted", "arithmetic/acquired-batch-more",
])
@pytest.mark.parametrize("seed",[0,1,2])
def test_premises_generate_and_round_trip(rule,seed):
    from rulekit.generation import generate_candidate
    result=generate_candidate(load_project(Path("projects/curated")),rule_id=rule,seed=seed)
    assert result.target_status == "matched",result

@pytest.mark.parametrize("text",[
    "Nora downloaded 100 of Tova's files and deleted half of them. How many files remain?",
    "Nora downloaded 100 files and deleted half of them. How many red files does Nora have left?",
    "Nora downloaded 100 files and deleted half of them. How many files does Tova have left?",
    "Nora downloaded 100 files and deleted half of them. How many files did Nora discard?",
    "Nora downloaded 100 files and deleted half of them. How many useful files did Nora delete?",
    "Nora downloaded 100 files. She lost 20 files. She deleted half of them. How many files remain?",
    "Nora downloaded 100 files and deleted half of them. She deleted half of them. How many files remain?",
    "Nora downloaded 100 files and deleted half of them. She downloaded 60 files and deleted half of the remaining files. How many files remain?",
])
def test_no_silent_scope_or_event_substitution(reg,text):
    result=solve(text,reg)
    assert not result.answer.committed,result.answer

@pytest.mark.parametrize("fraction",["25%","one fourth","1/4"])
def test_positive_classification_and_explicit_last_round(reg,fraction):
    result=solve(f"Nora received 80 images and realized that {fraction} of them were useful. "
                 "She received 80 images and realized that half of them were helpful. "
                 "How many images remain after discarding the unrelated images she received in the last batch?",reg)
    assert result.answer.value == 120,result.answer

@pytest.mark.parametrize("fraction,expected",[("0%",100),("100%",0)])
def test_fraction_endpoints(reg,fraction,expected):
    result=solve(f"Nora collected 100 files and discarded {fraction} of them. How many files remain?",reg)
    assert result.answer.value == expected,result.answer


@pytest.mark.parametrize("text,expected",[
    ("Nora collected 100 apples. How many apples does Nora have?",100),
    ("Nora downloaded 100 files. How many files does Nora have left?",100),
    ("Nora downloaded 100 files. She received 60 files. She deleted half of them. How many files remain?",130),
    ("Nora downloaded 100 files and deleted half of them. How many files did Nora download?",100),
])
def test_acquisition_without_disposal_and_acquired_total(reg,text,expected):
    result=solve(text,reg)
    assert result.answer.value == expected,result.answer

@pytest.mark.parametrize("text",[
    "Nora's brother downloaded 100 files and deleted half of them. How many files remain?",
    "Nora downloaded Tova's 100 files and deleted half of them. How many files remain?",
    "Nora downloaded 100 files and deleted half of them because they were irrelevant. How many of Tova's useful files remain?",
])
def test_ownership_identity_cannot_be_erased(reg,text):
    result=solve(text,reg)
    assert not result.answer.committed,result.answer


def test_unnumbered_removal_cannot_choose_between_classified_batches(reg):
    result=solve("Nora downloaded 100 files and realized that half of them were irrelevant. "
                 "She downloaded 200 files and realized that half of them were irrelevant. "
                 "How many files remain after deleting the irrelevant files?",reg)
    assert not result.answer.committed,result.answer
