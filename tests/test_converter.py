import json

from trankit_fnbr.converter import convert_conllu
from trankit_fnbr.domain import Lemma, Pattern
from trankit_fnbr.lexical import LexicalProcessor
from trankit_fnbr.repository import InMemoryLexiconRepository


SOURCE = """# sent_id = s1
# text = Ele chegou em primeiro lugar.
1\tEle\tele\tPRON\t_\t_\t2\tnsubj\t_\t_
2\tchegou\tchegar\tVERB\t_\t_\t0\troot\t_\t_
3\tem\tem\tADP\t_\t_\t5\tcase\t_\t_
4\tprimeiro\tprimeiro\tADJ\t_\t_\t5\tamod\t_\t_
5\tlugar\tlugar\tNOUN\t_\t_\t2\tadvmod\t_\tSpaceAfter=No
6\t.\t.\tPUNCT\t_\t_\t2\tpunct\t_\t_
"""


def test_converter_projects_tree_and_writes_fnbr_type_and_manifest() -> None:
    repository = InMemoryLexiconRepository(
        revision="snapshot-1",
        forms={
            "ele": [Lemma(1, "ele", "reference", "PRON")],
            "chegou": [Lemma(2, "chegar", "event", "VERB")],
            ".": [],
        },
        patterns=[Pattern(8, "em primeiro lugar", "em primeiro lugar", "connection", True)],
    )

    converted, manifest = convert_conllu(
        SOURCE,
        LexicalProcessor(repository),
        source_name="fixture.conllu",
        converter_version="test",
    )

    assert "3\tem primeiro lugar\tem primeiro lugar\tNOUN\t_\t_\t2\tadvmod\t_\tFNBRType=connection" in converted
    assert "2\tchegou\tchegar\tVERB\t_\t_\t0\troot\t_\tFNBRType=event" in converted
    assert manifest["lexicon_revision"] == "snapshot-1"
    assert manifest["source_files"][0]["name"] == "fixture.conllu"
    assert len(manifest["source_files"][0]["sha256"]) == 64
    assert len(manifest["output_sha256"]) == 64
    assert manifest["instances"][0]["source_sentence_id"] == "s1"
    assert any(item["lexical_token_id"].startswith("lemma:8:") for item in manifest["instances"][0]["lattice"])
