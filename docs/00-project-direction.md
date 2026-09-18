# Trankit FNBr: project direction

`trankit_fnbr` is a separate fork of Trankit for an FNBr-specific second parsing pass. It does not replace ordinary Universal Dependencies parsing, WebTool's lexical graph, FrameNet interpretation, or the future Pre-Frame Semantic Graph.

Its purpose is to consume the **MWE-aware, non-overlapping lexical sequence selected by WebTool** and return:

- a contextual distribution over FNBr's 15 lemma types;
- a dependency scaffold over those lexical units;
- provenance and confidence needed by later FNBr interpretation.

The 15 types are six conceptual types — `event`, `object`, `role`, `relation`, `quality`, `value` — and nine procedural types — `reference`, `quantification`, `polarity`, `degree`, `modality`, `connection`, `focus`, `predication`, `interaction`.

A dedicated `lemma_type` prediction head must be added to the fork. Do **not** overload Trankit's `UPOS` or `XPOS`: they remain available for their ordinary syntactic role, while FNBr typing is an independent semantic prediction.

## Build sequence

1. Pin and document the upstream Trankit revision.
2. Add the `lemma_type` head, training labels, top-k probabilities, and API output.
3. Convert one Portparser split — initially `h8418_0_{train,dev,test}` — through the same WebTool lexical segmentation used at runtime. Do not concatenate the ten random variants, because they are alternative splits of the same Porttinari corpus.
4. Project each UD tree onto the selected lexical-unit sequence, collapsing selected MWEs while retaining the full WebTool token lattice as provenance.
5. Assign lemma-type labels from the selected FNBr lemma. Record unresolved and ambiguous cases for review rather than silently treating them as gold.
6. Train and evaluate contextual type prediction before attempting a new semantic dependency grammar.
7. Use the resulting typed lexical dependency scaffold to build the Pre-Frame Semantic Graph.

## Boundary

The Trankit output remains a tree-shaped scaffold. The Pre-Frame Semantic Graph may add alternatives, MWE/component relations, implicit nodes, coreference, scope, multiple semantic edges, schema hypotheses, microframe hypotheses, and frame hypotheses. It is therefore not constrained by Trankit's one-head-per-token dependency structure.
