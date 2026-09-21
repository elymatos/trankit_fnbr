# Domain glossary

## FNBr lexical projection

A sentence-level representation whose units are selected FNBr lexical units rather than only syntactic words. A unit may be an ordinary word or an MWE. Each selected unit retains its lexical candidates, source span, and dependencies projected from the word-level UD analysis.

## Lexical type

The type recorded for an FNBr lemma in the authoritative lexicon. It is a defeasible lexical default, not a claim that every occurrence has that interpretation.

## Contextual type prediction

A ranked distribution over FNBr lemma types for a lexical-unit occurrence in context. It is evidence alongside the lexical type and does not overwrite the lexicon.

## Lexical ambiguity

An occurrence for which lexical lookup yields multiple plausible FNBr lemmas. Returning the candidate set preserves ambiguity; choosing the intended lemma is contextual lexical disambiguation.

## Contextual lexical disambiguation

Selection or ranking of FNBr lemma candidates using evidence from the occurrence's context. Type prediction contributes to disambiguation only when its output is connected back to candidate ranking.

## Dependency scaffold

A syntactic attachment structure over selected FNBr lexical units. Initially it is projected from the word-level UD tree and is not a semantic dependency analysis.

## FNBr-aware parse

An FNBr lexical projection with lexical types and a dependency scaffold. Contextual type predictions may be included, but a trained contextual model is not required for the baseline representation.
