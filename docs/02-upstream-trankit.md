# Upstream Trankit baseline

The vendored fork under `trankit/` was created from:

- repository: <https://github.com/nlp-uoregon/trankit>
- revision: `54e863327391262cf72f6adc1b0ff104e972a1dc`
- upstream package version: `1.1.2`
- revision date: 2025-07-22

The upstream Git metadata is intentionally not vendored. Changes specific to FNBr are tracked by this repository's Git history.

## FNBr modifications

- `FNBRType` labels are read from CoNLL-U `MISC`.
- the tagger dataset batches the fifteen FNBr labels independently from UPOS and XPOS;
- `PosDepClassifier` has an independent `lemma_type_ffn` head;
- the head contributes cross-entropy loss for labeled training tokens;
- inference returns the complete probability ranking so callers can request any top-k value;
- ordinary upstream checkpoints without an FNBr vocabulary continue to work without creating the additional head.
