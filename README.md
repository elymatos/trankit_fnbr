# Trankit FNBr

A self-contained FNBr lexical-analysis service. It performs Portuguese UD parsing, reads FNBr lexical data directly from MariaDB, recognizes words and MWEs, selects a deterministic non-overlapping lexical sequence, projects the UD tree onto that sequence, and predicts contextual FNBr lemma types.

See [`docs/01-specification.md`](docs/01-specification.md) for the complete contract and [`docs/02-upstream-trankit.md`](docs/02-upstream-trankit.md) for the pinned Trankit baseline.

## Environment

All local installation and development commands use Conda:

```bash
conda env create -f environment.yml
conda activate trankit-fnbr
cp .env.example .env
```

Configure `FNBR_DATABASE_URL` with a MariaDB account that has `SELECT` only. Set `FNBR_LEXICON_REVISION` to an identifiable snapshot or deployment revision. Credentials and model caches are not committed.

## API

```bash
conda run -n trankit-fnbr fastapi run main.py --port 8000
```

Analyze raw text:

```http
POST /fnbr/
Content-Type: application/json

{"text": "Ele chegou em primeiro lugar.", "top_k": 3}
```

The response includes selected lexical units, alternative lattice analyses, source spans, FNBr identifiers, top-k lemma-type probabilities, projected dependencies, and model/schema/lexicon provenance.

## Dataset conversion

The default safety gate accepts only the first experimental split, `h8418_0`:

```bash
conda run -n trankit-fnbr python scripts/convert_dataset.py \
  datasets/h8418_0_train.conllu outputs/h8418_0_train.fnbr.conllu
```

A JSON provenance manifest is written beside the converted file. Pass `--allow-other-split` only for an explicitly planned experiment. Never combine split variants `0`–`9`.

## Training the FNBr head

Converted files store labels as `FNBRType=<type>` in CoNLL-U `MISC`. The vendored Trankit `posdep` training task reads these labels and trains an independent fifteen-way head:

```python
from trankit import TPipeline

trainer = TPipeline({
    "task": "posdep",
    "category": "customized",
    "train_conllu_fpath": "outputs/h8418_0_train.fnbr.conllu",
    "dev_conllu_fpath": "outputs/h8418_0_dev.fnbr.conllu",
    "save_dir": "./cache/fnbr",
    "embedding": "xlm-roberta-large",
    "lemma_type_only": True,  # establish the type-only baseline first
    "gpu": True,
})
trainer.train()
```

After measuring the baseline, remove `lemma_type_only` (or set it to `False`) to train jointly with projected POS/dependency objectives.

## Verification

```bash
conda run -n trankit-fnbr python -m pytest
conda run -n trankit-fnbr mypy trankit_fnbr
```
