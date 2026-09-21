# Trankit FNBr specification

## Status

Draft for the first FNBr-specific Trankit extension.

This specification supersedes prior implementation assumptions that made WebTool part of the runtime pipeline. WebTool remains a reference for existing FNBr lexical-processing behavior, but `trankit_fnbr` implements and owns that behavior in Python.

## 1. Purpose

FrameNet Brasil needs a representation of text meaning before a lexical frame has been selected. The first computational step toward that representation is a contextual analysis over **FNBr lexical units**, including fixed and variable MWEs, rather than only over UD word tokens.

`trankit_fnbr` provides that step as a self-contained pipeline. Starting from raw text, it performs standard Portuguese analysis, reads lexical data directly from the FNBr database, recognizes lexical candidates and MWEs, selects a non-overlapping lexical-unit sequence, and predicts a contextual FNBr lemma type and dependency scaffold over that sequence.

The core principle is:

> Text meaning should be representable before the system knows which lexical frame it instantiates.

This is not a proposal to replace UD or FrameNet. It adds an occurrence-level bridge between them without requiring another application to preprocess runtime input.

## 2. Scope

### In scope

- a maintained fork of Trankit;
- a new contextual `lemma_type` classifier over 15 FNBr types;
- training-data conversion from Portparser CoNLL-U files;
- a Python implementation of FNBr lexical lookup, candidate recognition, and MWE-aware segmentation;
- direct, read-only access to a versioned FNBr database schema;
- token-lattice construction and deterministic selection of a non-overlapping lexical sequence;
- projection of a UD dependency tree onto the selected lexical units;
- top-k type probabilities and type-aware API output;
- evaluation of type prediction, MWE-aware parsing, and lexical disambiguation benefit.

### Out of scope for the first version

- replacing the first UD parsing pass;
- integration with or runtime dependence on WebTool;
- editing or administering FNBr lexical data;
- a complete semantic dependency grammar;
- direct prediction of frames, FEs, schemas, or microframes;
- coreference, implicit participants, document-level temporal structure, or unrestricted scope;
- automatic creation of frames or microframes.

## 3. Components and responsibilities

All runtime components below belong to this repository and are exposed as one pipeline.

| Component | Responsibility |
|---|---|
| Standard Trankit pass | Portuguese tokenization, UPOS, morphology, and UD parsing over syntactic words. |
| FNBr database adapter | Read forms, lemmas, lemma types, fixed and variable MWE definitions, constructions, and stable identifiers from the FNBr database. |
| Python lexical processor | Perform form/lemma lookup, recognize fixed MWEs, variable patterns, and constructions, and build candidate analyses with token-span provenance. |
| Sequence selector | Deterministically choose a non-overlapping linear projection containing ordinary lexical tokens and selected MWE tokens. |
| Trankit FNBr pass | Produce contextual lemma-type probabilities and a lexical-unit dependency scaffold over the selected sequence. |
| API layer | Accept raw text and return the selected sequence, lattice provenance, model predictions, and dependency scaffold. |

The lexical processor persists a token lattice, not merely a linear sequence. For example, it can retain both `em`, `primeiro`, `lugar` and a candidate span `em primeiro lugar`. The full lattice remains evidence, while the FNBr model consumes only the selected, non-overlapping projection.

Every MWE is a lemma. The selected MWE token must therefore carry its selected lemma through the same domain representation used for a single-word token.

WebTool is neither called nor imported at runtime. Its current behavior and documentation may be used to derive compatibility tests while the required algorithms are ported to Python. Once specified here, this repository's tests and versioned lexical-processing rules define pipeline behavior.

## 4. Self-contained two-pass pipeline

```text
Raw sentence
  ↓
Trankit 1: standard UD parsing over syntactic words
  ↓
Python FNBr lexical processor + direct database lookup
  ↓
Token lattice + deterministic non-overlapping lexical sequence
  ↓
Trankit FNBr: lemma-type distribution + lexical dependency scaffold
  ↓
Pipeline response
```

The two model passes have distinct jobs:

| Pass | Input units | Output purpose |
|---|---|---|
| Trankit 1 | syntactic words | conventional UD evidence used by lexical recognition and dependency projection |
| Trankit FNBr | selected FNBr lexical units, including MWEs | contextual typing and lexical-unit attachment scaffold |

The database lookup and lexical-processing stages between the two passes are first-class parts of `trankit_fnbr`, not external preprocessing.

## 5. FNBr lemma types

The label inventory is defined by the FNBr lemma-typing specification. A lemma has exactly one type; an LU inherits its lemma's type. When the same form and POS have readings of different types, they are distinct lemmas.

### 5.1 Conceptual types

| Type | Expected interpretive contribution |
|---|---|
| `event` | candidate event occurrence |
| `object` | candidate discourse entity |
| `role` | candidate entity whose interpretation depends externally on a relation/situation |
| `relation` | candidate reified relational situation |
| `quality` | candidate dimension or quality |
| `value` | candidate region/value within a quality dimension |

### 5.2 Procedural types

| Type | Expected operational contribution |
|---|---|
| `reference` | introduce or resolve a referent |
| `quantification` | quantify a node or situation |
| `polarity` | affirm or deny a scope candidate |
| `degree` | locate/modify a value relative to a standard |
| `modality` | qualify possibility, necessity, or commitment |
| `connection` | connect propositions or discourse units |
| `focus` | mark information-structural foregrounding |
| `predication` | mediate construction of a predication without conceptual content |
| `interaction` | mark source, speaker/hearer management, stance display, or related interactional work |

A type is a lexical default and is defeasible in use. `trankit_fnbr` predictions must rank interpretations; they must not make irreversible frame or coercion decisions.

## 6. Model changes

### 6.1 Dedicated head

Add a dedicated `lemma_type` classification head to Trankit's POS/dependency model. It has:

- a vocabulary of the fifteen types;
- a feed-forward classifier over the token representation;
- cross-entropy loss during training;
- probabilities, not only the argmax label, during inference.

The head is independent of UPOS, XPOS, morphological features, head prediction, and dependency-label prediction.

Do not encode FNBr types by replacing UPOS or XPOS. This would conflate the conceptual/procedural analysis with POS and would be especially misleading for MWEs, whose POS is legitimately absent in the FNBr lexicon.

### 6.2 Output contract

For every selected lexical token, return at least:

```json
{
  "text": "em primeiro lugar",
  "selected_lemma_id": 123,
  "lemma_type_candidates": [
    {"type": "connection", "probability": 0.87},
    {"type": "relation", "probability": 0.08}
  ],
  "head": 5,
  "deprel": "advmod"
}
```

The API must preserve enough identifiers to reconnect each output item to the pipeline's selected token, FNBr database lemma, original character and token spans, and source components. The exact response schema is an implementation detail, but this information is mandatory.

### 6.3 Dependency scaffold

For the first model, HEAD and DEPREL are a projected UD tree over lexical units. They are not yet a semantic dependency grammar.

A downstream consumer may interpret combinations such as:

| Dependent type | Head type | Projected UD relation | Candidate interpretation |
|---|---|---|---|
| `polarity` | `event` | `advmod` | polarity scope candidate |
| `degree` | `value` | `advmod` | degree/value attachment |
| `reference` | `object` | `det` | reference operation on object |
| `modality` | `event` | `aux` or `advmod` | modal scope candidate |
| `connection` | event/clause | `mark` or `advmod` | discourse/proposition connection candidate |
| `predication` | conceptual predicate | `cop`, `case`, or `aux` | predication operation |

These mappings are proposal rules, not semantic truth conditions. `nsubj` and `obj`, for example, provide participant attachment evidence but do not by themselves decide Agent, Patient, or another Frame Element.

## 7. Dataset conversion

### 7.1 Source corpus

The source is Portparser's Porttinari/Porttinari-base UD corpus, stored under:

```text
/home/ematos/devel/python/Portparser/datasets/
```

Files are organized as `hXXXX_Y_{train,dev,test}.conllu`, where `XXXX` is corpus size and `Y` is one of ten random split variants.

The first experiment uses exactly:

```text
h8418_0_train.conllu
h8418_0_dev.conllu
h8418_0_test.conllu
```

Do not combine variants `0`–`9`: they are alternative random versions of the same corpus, not disjoint corpora. Combining them would leak duplicated sentences across train, development, and test data.

### 7.2 Conversion input and reproducibility

For every Portparser sentence:

1. read the `# text` comment and original CoNLL-U tree;
2. run the same in-repository Python lexical processor and database adapter used at runtime;
3. select one non-overlapping lexical sequence;
4. preserve the source sentence ID, source CoNLL-U token IDs, internal lexical-token IDs, MWE component spans, selected database lemma IDs, and tokenizer, lexical-rule, schema, and lexicon versions;
5. emit the converted training instance.

A conversion run must record:

- Portparser source files and checksums;
- `trankit_fnbr` commit;
- FNBr database schema version and lexicon snapshot identifier;
- lexical-processing and segmentation-policy versions;
- converter version;
- generated dataset checksums.

A model without this provenance is not reproducible because a changed MWE inventory changes its input sequence and labels.

### 7.3 Selected segmentation

The selected sequence is a linear projection of the token lattice built by the in-repository lexical processor. It may replace several component words with one MWE token. The lattice and rejected alternatives are retained in metadata but cannot be fed directly to Trankit.

Selection must be deterministic for the first experiment. The policy must be stated in the converter and tested. It should at minimum define precedence between reviewed MWEs, fixed MWEs, variable patterns, constructions, overlapping spans, and unresolved candidates.

### 7.4 Dependency projection

For each selected MWE span:

1. identify its syntactic head among the original UD words;
2. collapse the span into one lexical token;
3. remove internal dependencies of the collapsed span;
4. give the lexical token the collapsed head's external HEAD and DEPREL;
5. redirect every external dependent of an absorbed component to the lexical token;
6. renumber token IDs and HEAD values;
7. validate that the result has one root, one head per non-root node, no cycles, and a connected tree.

The converter must not invent a semantic head merely because the MWE is semantically meaningful. The first-stage tree is a projected syntactic scaffold.

### 7.5 Type labels

The selected FNBr lemma supplies the initial gold `FNBRType` label.

Cases must be separated into:

- **resolved:** one selected lemma with a known type;
- **ambiguous:** several plausible lemma analyses with different types;
- **unresolved:** no selected lemma or no migrated type;
- **coercion/constructional:** the lexical default may be overridden by the construction.

Only reviewed or high-confidence resolved labels may serve as ordinary supervised gold. Ambiguous and unresolved cases must remain measurable; dropping them silently would produce misleading metrics and hide precisely the hard lexical cases the model should eventually assist.

### 7.6 Storage format

Use valid CoNLL-U for the projected dependency tree. Store the type label in the extensible MISC column:

```text
FNBRType=event
```

Example:

```text
1  João              João              PROPN  _  _  3  nsubj   _  FNBRType=object
2  não               não               ADV    _  _  3  advmod  _  FNBRType=polarity
3  abriu             abrir             VERB   _  _  0  root     _  FNBRType=event
4  em primeiro lugar em_primeiro_lugar _      _  _  3  advmod   _  FNBRType=connection
```

The Trankit FNBr reader must explicitly load `FNBRType` from MISC. CoNLL-U tools that do not know the extension can still read the projected tree.

## 8. Runtime API

The primary endpoint accepts raw text. A caller does not need to know the FNBr database schema, identify lexical candidates, resolve overlapping MWEs, or construct a pre-tokenized lexical sequence.

```text
Raw text
  → standard Trankit pass
  → FNBr database lookup and Python lexical processing
  → deterministic lexical-sequence selection
  → Trankit FNBr pass
  → selected tokens + lattice provenance + type probabilities + scaffold dependencies
```

A lower-level pre-tokenized interface may exist for training, tests, and diagnostics, but it is not the primary integration contract and must not bypass provenance validation silently.

Selected lexical units may contain spaces. Before implementation, test how Trankit's XLM-R tokenization treats an item such as `em primeiro lugar`. Preserve its human-readable form, component token IDs, and character offsets regardless of the internal wordpiece representation.

The response must identify the model version, lexical-processing policy version, database schema version, and lexicon snapshot or revision used. It must include unresolved and ambiguous lexical analyses rather than silently discarding them.

## 9. Direct FNBr database access

### 9.1 Data ownership and access mode

The FNBr database is the authoritative source for lexical records. `trankit_fnbr` accesses it through a repository-owned Python data-access layer. All SQL and schema-specific mapping must remain behind that layer so model and pipeline code use stable domain objects rather than database rows.

Runtime access is read-only. This project must not create, update, or delete FNBr records. Credentials are supplied through deployment configuration, never committed to the repository or included in API output and dataset provenance.

### 9.2 Required lexical data

The adapter must expose, with stable FNBr identifiers where available:

- forms and normalized forms;
- lemmas and their fifteen-way types;
- form-to-lemma analyses;
- fixed MWE definitions and components;
- variable MWE or pattern definitions required by recognition;
- constructions and constraints required by sequence selection;
- the database schema version and a lexicon snapshot or revision identifier.

The exact tables and joins are adapter implementation details. Before coding the adapter, map the deployed FNBr schema and add fixture-backed contract tests for each required query.

### 9.3 Reproducibility and failure behavior

Training conversion must use an immutable database snapshot or exported lexical snapshot. Runtime may use a live read replica, but every result must report the identifiable lexicon revision used. Caches must be invalidated or namespaced by that revision.

The service must fail clearly when the database is unavailable, the schema version is unsupported, or the lexical revision cannot be identified. It must not continue with an unreported stale or partial lexicon. Connection pooling, query timeouts, and bounded caches are required deployment concerns; their concrete values remain configurable.

## 10. Training and evaluation

### 10.1 Training stages

1. Implement and validate the read-only FNBr database adapter against a pinned schema and lexical snapshot.
2. Port lexical lookup, MWE and construction recognition, lattice construction, and deterministic selection to Python, with compatibility fixtures derived from reviewed examples.
3. Verify conversion and projected-tree validity without modifying Trankit.
4. Add and test `lemma_type` training and inference.
5. Train type prediction over the converted `h8418_0` split.
6. Train jointly with projected dependency prediction only after the type-only baseline is measured.
7. Evaluate whether top-k predictions improve contextual lemma-candidate ranking inside the self-contained pipeline.

### 10.2 Required metrics

Report:

- lemma-type accuracy;
- macro-F1 and per-type F1 across all fifteen types;
- conceptual-versus-procedural F1;
- confusion matrix;
- top-2 and top-3 type recall;
- results for tokens with multiple candidate lemmas of different types;
- MWE recognition, segmentation, and selected-lemma coverage;
- projected-tree UAS/LAS;
- database lookup, conversion, unresolved-label, and excluded-instance counts;
- lexical-processor compatibility results for reviewed reference fixtures.

Do not report only aggregate accuracy: frequent categories can conceal failure on `role`, `connection`, `modality`, `interaction`, and other semantically decisive types.

### 10.3 Decision gate

Proceed to semantic dependency labels or frame matching only when:

- direct database lookup is covered by schema contract tests;
- lexical processing and sequence selection are deterministic for a fixed input and lexicon revision;
- the converter validates all projected trees;
- type metrics are reported by category, not merely globally;
- uncertainty is exposed in the pipeline response;
- type prediction demonstrably improves contextual lemma disambiguation or otherwise supplies useful downstream evidence.

## 11. Implementation work packages

### WP1 — Fork baseline

- Record upstream Trankit revision and local modifications.
- Establish tests that confirm original Portuguese parsing behavior remains available.

### WP2 — FNBr database adapter

- Document the supported database engine and schema version.
- Configure read-only, pooled access without storing credentials in source control.
- Map database records to typed Python representations for forms, lemmas, types, MWEs, patterns, and constructions.
- Add fixture-backed query contract tests and explicit schema-compatibility checks.
- Expose a lexicon revision suitable for provenance and cache namespacing.

### WP3 — Python lexical processor

- Implement normalization and form/lemma lookup.
- Implement fixed MWE, variable-pattern, and construction recognition required by the pipeline.
- Build the complete token lattice with source spans and candidate provenance.
- Implement and version deterministic overlap resolution and sequence selection.
- Add reviewed compatibility fixtures for ordinary words, contractions, fixed and variable MWEs, constructions, overlaps, ambiguity, and unresolved input.

### WP4 — Data converter

- Read Portparser CoNLL-U.
- Run the same database adapter, lexical processor, and selector used at runtime.
- Project the tree and write extended CoNLL-U plus provenance metadata.
- Add unit tests for ordinary tokens, MWE collapse, external dependents, roots, contractions, and overlapping candidates.

### WP5 — Lemma-type model

- Add vocabulary, dataset reader, batch fields, classifier head, loss, prediction probabilities, serialization, and evaluation.
- Add regression tests for dataset loading and pipeline output.

### WP6 — Self-contained API

- Add a raw-text FNBr endpoint that orchestrates both Trankit passes, direct lexical lookup, lexical processing, sequence selection, and dependency projection.
- Return selected and alternative analyses, stable FNBr identifiers, spans, provenance versions, top-k type candidates, and scaffold dependencies.
- Keep any pre-tokenized endpoint explicitly lower-level and suitable for tests or controlled internal use.

## 12. Open questions

1. Which deployed FNBr database engine, schema version, and tables are authoritative for this project?
2. What mechanism identifies an immutable lexicon snapshot for training and a revision for live runtime queries?
3. What deterministic policy selects among reviewed MWEs, fixed MWEs, variable patterns, constructions, overlapping spans, and unresolved candidates?
4. Which existing lexical-processing behaviors must be reproduced exactly, and which may be redesigned in the Python implementation?
5. How should Trankit's wordpiece tokenizer receive multiword lexical units: original spaces, an escaped form, or an adapter-level representation?
6. Which labels may be generated automatically from the migrated lemma inventory, and which require human review?
7. Should the first model train all dependency tasks jointly or initially train the new head against frozen/projected syntactic evidence?
8. How should constructional coercion be represented in training data without making a defeasible lexical type appear incorrect?
9. How much does contextual type prediction improve same-form/same-POS lemma disambiguation over lexical lookup alone?
10. Should runtime use a live read replica, a synchronized local lexical snapshot, or support both modes?

## 13. Sources

- FNBr lemma typing design: `app/UI/views/Documentation/ontological_dimension/lemmas.md` in the WebTool repository.
- Existing lexical-processing behavior used as a porting reference: `docs/lexicon/lexicon-architecture.html` in the WebTool repository.
- Portparser dataset and provenance: `/home/ematos/devel/python/Portparser/README.md`.
- Trankit source, customized training, and POS/dependency architecture: upstream Trankit repository and the forked `trankit/` directory.
