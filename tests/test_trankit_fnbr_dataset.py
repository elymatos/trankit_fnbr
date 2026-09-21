from types import SimpleNamespace

import torch

from trankit.iterators.tagger_iterators import TaggerDataset


class Tokenizer:
    def tokenize(self, word):
        return [word]

    def encode(self, pieces, **kwargs):
        return [0] + list(range(1, len(pieces) + 1)) + [2]


def test_tagger_dataset_batches_fnbr_labels(tmp_path) -> None:
    conllu = tmp_path / "fixture.conllu"
    conllu.write_text(
        "1\tnão\tnão\tADV\t_\t_\t2\tadvmod\t_\tFNBRType=polarity\n"
        "2\tchegou\tchegar\tVERB\t_\t_\t0\troot\t_\tFNBRType=event\n\n",
        encoding="utf-8",
    )
    config = SimpleNamespace(
        treebank_name="fixture", save_dir=str(tmp_path), _save_dir=str(tmp_path),
        lang="fixture", wordpiece_splitter=Tokenizer(), max_input_length=512,
        device=torch.device("cpu"),
    )

    dataset = TaggerDataset(config, str(conllu), str(conllu), evaluate=False)
    dataset.numberize()
    batch = dataset.collate_fn([dataset[0]])

    assert batch.lemma_type_idxs.tolist() == [8, 0]
