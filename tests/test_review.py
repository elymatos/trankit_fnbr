import pytest

from trankit_fnbr.review import apply_review, export_review

CONLLU = """# sent_id = s1
# text = Mais tarde de casa .
1\tMais tarde\tmais tarde\tADV\t_\t_\t0\troot\t_\tFNBRType=reference
2\tde\tde\tADP\t_\t_\t3\tcase\t_\tFNBRStatus=ambiguous
3\tcasa\tcasa\tNOUN\t_\t_\t1\tobl\t_\tFNBRType=object
4\t.\t.\tPUNCT\t_\t_\t1\tpunct\t_\tFNBRStatus=unresolved
"""


def test_export_keeps_sentence_comments_and_one_label_per_token() -> None:
    assert export_review(CONLLU) == (
        "# sent_id = s1\n# text = Mais tarde de casa .\n"
        "1\tMais tarde\treference\n2\tde\tambiguous\n3\tcasa\tobject\n4\t.\tunresolved\n"
    )


def test_unedited_review_round_trips_unchanged() -> None:
    assert apply_review(CONLLU, export_review(CONLLU)) == (CONLLU, 0)


def test_apply_converts_between_types_and_statuses() -> None:
    review = (export_review(CONLLU)
              .replace("1\tMais tarde\treference", "1\tMais tarde\tconnection")
              .replace("2\tde\tambiguous", "2\tde\tconnection")
              .replace("3\tcasa\tobject", "3\tcasa\tunresolved"))
    updated, changed = apply_review(CONLLU, review)
    assert changed == 3
    misc = [line.split("\t")[9] for line in updated.splitlines() if line[:1].isdigit()]
    assert misc == ["FNBRType=connection", "FNBRType=connection",
                    "FNBRStatus=unresolved", "FNBRStatus=unresolved"]


@pytest.mark.parametrize("old, new, message", [
    ("3\tcasa\tobject", "3\tcasa\tobjeto", "unknown label"),
    ("3\tcasa\tobject", "3\tcaso\tobject", "does not match"),
    ("4\t.\tunresolved\n", "", "no token 4"),
])
def test_apply_rejects_invalid_reviews(old: str, new: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        apply_review(CONLLU, export_review(CONLLU).replace(old, new))
