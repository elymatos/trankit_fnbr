from trankit.utils.conll import FNBR_TYPE
from trankit.utils.posdep_utils import tget_examples_from_conllu


class Tokenizer:
    def tokenize(self, word):
        return [word]


def test_tagger_reader_loads_fnbr_type_from_misc(tmp_path) -> None:
    conllu = tmp_path / "fixture.conllu"
    conllu.write_text(
        "1\tchegou\tchegar\tVERB\t_\t_\t0\troot\t_\tFNBRType=event\n\n",
        encoding="utf-8",
    )

    vocabs, examples, _ = tget_examples_from_conllu(Tokenizer(), 512, str(conllu), get_vocab=True)

    assert examples[0][FNBR_TYPE] == ["event"]
    assert len(vocabs[FNBR_TYPE]) == 15
