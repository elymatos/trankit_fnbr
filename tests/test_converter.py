import json

from trankit_fnbr.converter import _parse_conllu, convert_conllu
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


def test_converter_reports_unaligned_offsets_instead_of_inventing_them() -> None:
    source = """# sent_id = mismatch
# text = Casa | Um baile
1\tCasa\tcasa\tNOUN\t_\t_\t0\troot\t_\t_
2\t,\t,\tPUNCT\t_\t_\t1\tpunct\t_\t_
3\tum\tum\tDET\t_\t_\t4\tdet\t_\t_
4\tbaile\tbaile\tNOUN\t_\t_\t1\tappos\t_\t_
"""
    _, manifest = convert_conllu(
        source, LexicalProcessor(InMemoryLexiconRepository("fixture", {}, [])),
        "mismatch", "test"
    )
    assert manifest["unaligned_surface_tokens"] == 1
    assert manifest["instances"][0]["selected"][1]["start_char"] == -1
    assert manifest["instances"][0]["selected"][2]["start_char"] == 7


def test_contraction_anchor_avoids_cycle_from_external_dependent() -> None:
    source = """# sent_id = cycle
# text = mais dum ano
1\tmais\tmais\tADV\t_\t_\t3\tadvmod\t_\t_
2-3\tdum\t_\t_\t_\t_\t_\t_\t_\t_
2\tde\tde\tADP\t_\t_\t1\tfixed\t_\t_
3\tum\tum\tNUM\t_\t_\t4\tnummod\t_\t_
4\tano\tano\tNOUN\t_\t_\t0\troot\t_\t_
"""
    _, tokens, _ = _parse_conllu(source)[0]
    assert [(token.text, token.head) for token in tokens] == [
        ("mais", 2), ("dum", 4), ("ano", 0)
    ]
    converted, _ = convert_conllu(
        source, LexicalProcessor(InMemoryLexiconRepository("fixture", {}, [])),
        "cycle", "test"
    )
    assert "2\tdum\tum\tNUM\t_\t_\t3\tnummod" in converted


def test_converter_uses_surface_contractions_and_preserves_original_word_ids() -> None:
    source = """# sent_id = contracted
# text = Ela gosta das meninas.
1\tEla\tela\tPRON\t_\t_\t2\tnsubj\t_\t_
2\tgosta\tgostar\tVERB\t_\t_\t0\troot\t_\t_
3-4\tdas\t_\t_\t_\t_\t_\t_\t_\t_
3\tde\tde\tADP\t_\t_\t5\tcase\t_\t_
4\tas\to\tDET\t_\t_\t5\tdet\t_\t_
5\tmeninas\tmenina\tNOUN\t_\t_\t2\tobl\t_\tSpaceAfter=No
6\t.\t.\tPUNCT\t_\t_\t2\tpunct\t_\t_
"""
    comments, tokens, source_ids = _parse_conllu(source)[0]
    assert [(token.id, token.text, token.head, token.start_char, token.end_char)
            for token in tokens] == [
        (1, "Ela", 2, 0, 3), (2, "gosta", 0, 4, 9),
        (3, "das", 5, 10, 13), (5, "meninas", 2, 14, 21),
        (6, ".", 2, 21, 22),
    ]
    assert source_ids[3] == (3, 4)
    repository = InMemoryLexiconRepository("snapshot", {"das": [Lemma(12, "das", "reference")]}, [])
    converted, manifest = convert_conllu(source, LexicalProcessor(repository), "contractions", "test")
    assert "3\tdas\tdas\tADP\t_\t_\t4\tcase\t_\tFNBRType=reference" in converted
    assert manifest["instances"][0]["selected"][2]["source_word_ids"] == [3, 4]
