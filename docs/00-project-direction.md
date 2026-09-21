# Trankit FNBr: project direction

`trankit_fnbr` is a self-contained FNBr NLP pipeline built from a maintained fork of Trankit. It does not replace ordinary Universal Dependencies parsing or FrameNet interpretation.

The project owns the complete processing path from raw text to an MWE-aware lexical dependency scaffold. It must not require WebTool to tokenize text, recognize lexical candidates, select MWEs, or prepare runtime requests. The equivalent lexical-processing behavior will be implemented in Python in this repository and will read the FNBr lexical data directly from the database.

The pipeline must:

- run standard Portuguese tokenization and UD parsing;
- query the FNBr database for forms, lemmas, fixed and variable MWEs, and constructions needed by lexical recognition;
- build a token lattice and deterministically select an MWE-aware, non-overlapping lexical sequence;
- predict a contextual distribution over FNBr's 15 lemma types;
- project the UD tree onto the selected lexical units;
- return provenance and confidence for every lexical decision.

The 15 types are six conceptual types — `event`, `object`, `role`, `relation`, `quality`, `value` — and nine procedural types — `reference`, `quantification`, `polarity`, `degree`, `modality`, `connection`, `focus`, `predication`, `interaction`.

A dedicated `lemma_type` prediction head must be added to the fork. Do **not** overload Trankit's `UPOS` or `XPOS`: they remain available for their ordinary syntactic role, while FNBr typing is an independent semantic prediction.

## Build sequence

1. Pin and document the upstream Trankit revision.
2. Specify the FNBr database connection, supported schema version, read-only access policy, and reproducible snapshot mechanism.
3. Port the required lexical-processing behavior to Python: lexical lookup, MWE and construction recognition, token-lattice construction, overlap resolution, and deterministic sequence selection.
4. Add the `lemma_type` head, training labels, top-k probabilities, and API output.
5. Convert one Portparser split — initially `h8418_0_{train,dev,test}` — through the same in-repository lexical processor used at runtime. Do not concatenate the ten random variants, because they are alternative splits of the same Porttinari corpus.
6. Project each UD tree onto the selected lexical-unit sequence, collapsing selected MWEs while retaining the full token lattice as provenance.
7. Assign lemma-type labels from the selected FNBr lemma. Record unresolved and ambiguous cases for review rather than silently treating them as gold.
8. Train and evaluate contextual type prediction before attempting a new semantic dependency grammar.

## Boundary

The project owns standard parsing, FNBr lexical lookup and recognition, lexical-sequence selection, contextual lemma typing, dependency projection, and their public API. The FNBr database remains the authoritative lexical-data source and is accessed directly through a repository-owned data-access layer.

The output remains a tree-shaped lexical scaffold with token-lattice provenance. Any downstream interpretation is outside this project's scope and is not constrained by Trankit's one-head-per-token dependency structure.
