# Trankit FNBr specification

## Status

Draft for the first FNBr-specific Trankit extension.

This specification consolidates the prior Trankit analysis notes from WebTool and supersedes their implementation choices where they conflict with the decisions below.

## 1. Purpose

FrameNet Brasil needs a representation of text meaning before a lexical frame has been selected. The first computational step toward that representation is a contextual analysis over **FNBr lexical units**, including fixed and variable MWEs, rather than only over UD word tokens.

`trankit_fnbr` provides that step. It predicts a contextual FNBr lemma type and a dependency scaffold over the lexical-unit sequence supplied by WebTool.

The core principle is:

> Text meaning should be representable before the system knows which lexical frame it instantiates.

This is not a proposal to replace UD, FrameNet, the WebTool lexer, or the Frame Meaning Representation. It adds an occurrence-level bridge between them.

## 2. Scope

### In scope

- a maintained fork of Trankit;
- a new contextual `lemma_type` classifier over 15 FNBr types;
- training-data conversion from Portparser CoNLL-U files;
- WebTool-compatible MWE-aware lexical segmentation;
- projection of a UD dependency tree onto the selected lexical units;
- top-k type probabilities and type-aware API output;
- evaluation of type prediction, MWE-aware parsing, and lexical disambiguation benefit.

### Out of scope for the first version

- replacing the first UD parsing pass;
- replacing WebTool MWE or construction recognition;
- a complete semantic dependency grammar;
- direct prediction of frames, FEs, schemas, or microframes;
- coreference, implicit participants, document-level temporal structure, or unrestricted scope;
- automatic creation of frames or microframes.

## 3. Existing systems and responsibilities

| Component | Responsibility |
|---|---|
| First Trankit pass in WebTool | Standard Portuguese tokenization, UPOS, morphology, and UD parsing over syntactic words. |
| WebTool lexical graph | Form/lemma recognition, fixed MWEs, variable patterns, constructions, candidate lemmas, and token-span provenance. |
| WebTool selected sequence | A non-overlapping linear projection containing ordinary lexical tokens and selected MWE tokens. |
| `trankit_fnbr` | Contextual lemma-type probabilities and a lexical-unit dependency scaffold over that selected sequence. |
| Pre-Frame Semantic Graph | Interprets the scaffold into conceptual nodes, procedural operators, unresolved relations, and later schema/frame hypotheses. |

The WebTool tokenizer persists a token lattice, not merely a linear sequence. For example, it can retain both `em`, `primeiro`, `lugar` and a selected span `em primeiro lugar`. The full lattice remains evidence. `trankit_fnbr` consumes only the selected, non-overlapping projection.

Every MWE is a lemma. The WebTool export must therefore attach its selected lemma to its MWE token through the same conceptual mechanism used for a single-word token.

## 4. Two-pass pipeline

```text
Raw sentence
  ↓
Trankit 1: standard UD parsing over syntactic words
  ↓
WebTool lexical graph: lemma candidates, MWE/pattern recognition, token lattice
  ↓
WebTool selected lexical sequence: non-overlapping words and MWEs
  ↓
Trankit FNBr: lemma-type distribution + lexical dependency scaffold
  ↓
Pre-Frame Semantic Graph
```

The two models have distinct jobs:

| Pass | Input units | Output purpose |
|---|---|---|
| Trankit 1 | syntactic words | conventional UD evidence for WebTool lexical recognition and later interpretation |
| Trankit FNBr | selected FNBr lexical units, including MWEs | contextual typing and lexical-unit attachment scaffold |

## 5. FNBr lemma types

The label inventory is defined by the FNBr lemma-typing specification. A lemma has exactly one type; an LU inherits its lemma's type. When the same form and POS have readings of different types, they are distinct lemmas.

### 5.1 Conceptual types

| Type | Expected graph contribution |
|---|---|
| `event` | candidate event occurrence |
| `object` | candidate discourse entity |
| `role` | candidate entity whose interpretation depends externally on a relation/situation |
| `relation` | candidate reified relational situation |
| `quality` | candidate dimension or quality |
| `value` | candidate region/value within a quality dimension |

### 5.2 Procedural types

| Type | Expected graph-building contribution |
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

The API must preserve enough identifiers to reconnect the output to WebTool's selected token, lemma, original spans, and source components. The exact response schema is an implementation detail, but this information is mandatory.

### 6.3 Dependency scaffold

For the first model, HEAD and DEPREL are a projected UD tree over lexical units. They are not yet a semantic dependency grammar.

A later semantic layer may deterministically interpret combinations such as:

| Dependent type | Head type | Projected UD relation | Initial graph operation |
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
2. call the same WebTool tokenizer/lexical graph export used at runtime;
3. select one non-overlapping lexical sequence;
4. preserve the source sentence ID, source CoNLL-U token IDs, WebTool token IDs, MWE component spans, selected lemma IDs, and tokenizer/lexicon versions;
5. emit the converted training instance.

A conversion run must record:

- Portparser source files and checksums;
- WebTool commit;
- FNBr database/lexicon snapshot identifier;
- lexical segmentation policy version;
- converter version;
- generated dataset checksums.

A model without this provenance is not reproducible because a changed MWE inventory changes its input sequence and labels.

### 7.3 Selected segmentation

The selected sequence is a linear projection of WebTool's token lattice. It may replace several component words with one MWE token. The lattice and rejected alternatives are retained in metadata but cannot be fed directly to Trankit.

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

## 8. Runtime integration

WebTool will send a selected pre-tokenized sequence to a dedicated FNBr endpoint. It must not send overlapping raw `token` rows.

```text
WebTool selected tokens + selected lemma IDs + span provenance
  → trankit_fnbr endpoint
  → contextual type probabilities + scaffold dependencies
  → WebTool Pre-Frame Semantic Graph builder
```

The service must accept pre-tokenized lexical units that may contain spaces. Before implementation, test how Trankit's XLM-R tokenization treats an input item such as `em primeiro lugar`. Preserve the human-readable form and component offsets regardless of the internal wordpiece representation.

## 9. From scaffold to Pre-Frame Semantic Graph

The Trankit FNBr output is not the final meaning representation.

Conceptual types normally create candidate graph nodes. Procedural types create graph-building operations. Projected dependencies identify local attachment candidates. Later stages may add schema bindings, microframe hypotheses, frame hypotheses, null-instantiated roles, coreference, and non-local scope.

```text
Typed lexical dependency scaffold
  ↓
conceptual nodes + procedural operators + unresolved participant links
  ↓
schema and microframe hypotheses
  ↓
frame matching
```

The graph may have reentrancy and multiple edges, while Trankit's output must remain a dependency tree. The tree is evidence and a useful backbone, not a restriction on the graph's final form.

## 10. Training and evaluation

### 10.1 Training stages

1. Verify conversion and projected-tree validity without modifying Trankit.
2. Add and test `lemma_type` training and inference.
3. Train type prediction over the converted `h8418_0` split.
4. Train jointly with projected dependency prediction only after the type-only baseline is measured.
5. Integrate top-k predictions into WebTool lemma-candidate ranking.
6. Build a small reviewed Pre-Frame Semantic Graph pilot.

### 10.2 Required metrics

Report:

- lemma-type accuracy;
- macro-F1 and per-type F1 across all fifteen types;
- conceptual-versus-procedural F1;
- confusion matrix;
- top-2 and top-3 type recall;
- results for tokens with multiple candidate lemmas of different types;
- MWE segmentation and selected-lemma coverage;
- projected-tree UAS/LAS;
- conversion failures, unresolved labels, and excluded instances.

Do not report only aggregate accuracy: frequent categories can conceal failure on `role`, `connection`, `modality`, `interaction`, and other semantically decisive types.

### 10.3 Decision gate

Proceed to semantic dependency labels or frame matching only when:

- the converter is deterministic and validates all projected trees;
- type metrics are reported by category, not merely globally;
- uncertainty is returned to WebTool;
- type prediction demonstrably improves contextual lemma disambiguation or provides useful graph-building evidence.

## 11. Implementation work packages

### WP1 — Fork baseline

- Record upstream Trankit revision and local modifications.
- Establish tests that confirm original Portuguese parsing behavior remains available.

### WP2 — Data converter

- Read Portparser CoNLL-U.
- Obtain WebTool selected lexical segmentation and lemma data.
- Project the tree and write extended CoNLL-U plus provenance metadata.
- Add unit tests for ordinary tokens, MWE collapse, external dependents, roots, contractions, and overlapping candidates.

### WP3 — Lemma-type model

- Add vocabulary, dataset reader, batch fields, classifier head, loss, prediction probabilities, serialization, and evaluation.
- Add regression tests for dataset loading and API output.

### WP4 — API

- Add a dedicated pre-tokenized FNBr endpoint rather than changing the established UD endpoint silently.
- Return identifiers and top-k type candidates required by WebTool.

### WP5 — WebTool adapter

- Export selected sequence and provenance.
- Consume type probabilities.
- Build the initial typed lexical dependency scaffold.

## 12. Open questions

1. What deterministic policy selects among overlapping MWEs and constructions?
2. How should Trankit's wordpiece tokenizer receive multiword lexical units: original spaces, an escaped form, or an adapter-level representation?
3. Which labels may be generated automatically from the migrated lemma inventory, and which require human review?
4. Should the first model train all dependency tasks jointly or initially train the new head against frozen/projected syntactic evidence?
5. How should constructional coercion be represented in training data without making a defeasible lexical type appear incorrect?
6. Which procedural attachments can safely be converted into graph operations deterministically?
7. How much does contextual type prediction improve same-form/same-POS lemma disambiguation over lexical lookup alone?

## 13. Sources

- FNBr/WebTool lemma typing design: `app/UI/views/Documentation/ontological_dimension/lemmas.md` in the WebTool repository.
- WebTool lexical graph and tokenizer architecture: `docs/lexicon/lexicon-architecture.html` in the WebTool repository.
- Portparser dataset and provenance: `/home/ematos/devel/python/Portparser/README.md`.
- Trankit source, customized training, and POS/dependency architecture: upstream Trankit repository and the forked `trankit/` directory.
