# Trankit FNBr

A self-contained FNBr lexical-analysis service. It performs Portuguese UD parsing, reads FNBr lexical data directly from MariaDB, recognizes words and MWEs, selects a deterministic non-overlapping lexical sequence, projects the UD tree onto that sequence, and predicts contextual FNBr lemma types.

See [`docs/01-specification.md`](docs/01-specification.md) for the complete contract, [`docs/02-upstream-trankit.md`](docs/02-upstream-trankit.md) for the pinned Trankit baseline, and [`docs/03-pipeline-runtime.html`](docs/03-pipeline-runtime.html) for the implemented execution flow and parser-access options.

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

The response includes selected lexical units, alternative lattice analyses, source spans, FNBr identifiers, lexical types, top-k lemma-type probabilities, lexical-unit dependencies, and model/schema/lexicon provenance. With a joint checkpoint, `projected_head`/`projected_deprel` retain the original UD projection alongside model predictions.

## Docker HTTP service

The image uses the `trankit-fnbr` Conda environment. It does **not** contain credentials or model weights: Compose reads `.env` and mounts `./cache` at `/code/cache`. Ensure `cache/trankit/xlm-roberta-large/portuguese/` and `cache/fnbr-joint/xlm-roberta-large/customized/` contain the standard Portuguese model and trained joint checkpoint (including `fnbr.training.json`). Set `.env` to `FNBR_PREDICTOR_MODE=model`, `FNBR_SCAFFOLD_SOURCE=model`, `FNBR_TRANKIT_CACHE_DIR=./cache/fnbr-joint`, and the corresponding `FNBR_MODEL_VERSION` and `FNBR_LEXICON_REVISION`. The configured database must be reachable **from inside the container** with read-only credentials.

```bash
docker compose up --build -d
conda run -n trankit-fnbr python scripts/smoke_http.py
curl -sS http://127.0.0.1:8405/health/ready
curl -sS http://127.0.0.1:8405/fnbr/ -H 'Content-Type: application/json' \
  -d '{"text":"Ele tomou o café da manhã logo cedo.","top_k":3}'
```

`GET /health/live` checks only the HTTP process. `GET /health/ready` checks the loaded model and database connectivity, returning a generic 503 on failure. Compose publishes `127.0.0.1:8405` by default; set `FNBR_HTTP_BIND=0.0.0.0` in `.env` only behind a trusted reverse proxy with TLS and authentication. Set `FNBR_HTTP_PORT` to change the host port. The container runs one CPU worker to avoid duplicating two large XLM-R models. Do not expose this unauthenticated service directly to the Internet.

## Local sentence analysis

After configuring `.env`, run one sentence without starting the API:

```bash
conda run -n trankit-fnbr python scripts/analyze.py \
  "Ele chegou em primeiro lugar."
```

The default `--predictor lexical` mode requires the standard Portuguese Trankit model and FNBr database, but no trained FNBr checkpoint. It reports dictionary-derived lexical types and the projected dependency scaffold. To test a configured contextual checkpoint, pass `--predictor model`. Input can also be piped through standard input; use `--compact` for one-line JSON.

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

Or use the validated train/dev entry point (the test split is never used to select a checkpoint):

```bash
conda run -n trankit-fnbr python scripts/train_fnbr.py --epochs 5 --batch-size 4
conda run -n trankit-fnbr python scripts/evaluate_fnbr.py
```

The run uses provisional WebTool labels only for uniquely selected typed lemmas. Ambiguous and unresolved tokens remain in the projected tree but are masked from type loss and evaluation. The checkpoint is selected by development-set FNBr macro-F1; its UPOS/UAS/LAS scores are **not** meaningful in type-only mode. Test results are written to `outputs/h8418_0_test.metrics.json`. For runtime model mode, set `FNBR_TRANKIT_CACHE_DIR=./cache/fnbr`, `FNBR_PREDICTOR_MODE=model`, and an identifiable `FNBR_MODEL_VERSION` in the environment. The live-database timestamp revision identifies the conversion run but does not establish an immutable snapshot or independently reviewed occurrence labels.

For a separate jointly trained type/POS/dependency checkpoint, run:

```bash
conda run -n trankit-fnbr python scripts/train_fnbr.py --joint --epochs 5 --batch-size 4
conda run -n trankit-fnbr python scripts/evaluate_fnbr.py \
  --cache-dir ./cache/fnbr-joint --output outputs/h8418_0_test.joint.metrics.json
```

To test the joint checkpoint locally on raw text:

```bash
conda run -n trankit-fnbr python scripts/analyze.py --predictor model \
  --fnbr-cache-dir ./cache/fnbr-joint --scaffold-source model \
  --model-version h8418_0-joint-epoch3@202610021100 \
  "Ele tomou o café da manhã logo cedo."
```

To serve it, set `FNBR_TRANKIT_CACHE_DIR=./cache/fnbr-joint`, `FNBR_PREDICTOR_MODE=model`, `FNBR_SCAFFOLD_SOURCE=model`, and the corresponding `FNBR_MODEL_VERSION`. The response uses **learned lexical-unit dependencies** in `head`/`deprel`, retains `projected_head`/`projected_deprel` as the first-pass syntactic baseline, and identifies `scaffold_source`. Runtime verifies the joint-training metadata and checkpoint checksum. Leave `FNBR_SCAFFOLD_SOURCE=projected` for type-only checkpoints; their dependency weights are untrained. Test UAS/LAS in the evaluation JSON include punctuation and are measured against the automatically projected tree, **not** a semantic dependency grammar.

## Verification

```bash
conda run -n trankit-fnbr python -m pytest
conda run -n trankit-fnbr mypy trankit_fnbr
```
