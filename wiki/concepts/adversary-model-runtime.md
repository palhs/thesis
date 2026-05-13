# Adversary Model — Runtime

Companion page to [[concepts/adversary-model]] (T18). The main page pins
the adversary catalog — the generic capability × protocol matrix, the
per-capability bindings, and the protocol-specific attack surfaces. This
page pins the runtime obligations the implementation (T22) must hold: the
per-protocol intensity normalization, the uniform effect schema, the
`AdversaryProfile` reference sketch, the T27 determinism interaction, and
the open-to-revision register.

The split from [[concepts/adversary-model]] follows
`docs/wiki-spec.md` § Page size and mirrors the precedent of
[[concepts/network-model]] / [[concepts/network-model-phases]] and
[[concepts/simulation-design]] / [[concepts/simulation-design-runtime]].
Read the main page first for the catalog surface; this page assumes that
catalog as given.

## 1. Framing — relationship to main page

This page is the runtime companion to [[concepts/adversary-model]]. The
catalog page owns *what* attacks the simulator admits and *under which
invariant* each is classified; this page owns *how* an attack is
parameterised in a run, *which metric columns* it is expected to move,
*how* the profile data structure is shaped, and *how* the determinism
contract from [[concepts/node-model]] §8 extends to adversary-injected
events. The catalog ↔ runtime split keeps the comparison surface
(Chapter 4-facing) separate from the implementation surface (T22 / T27 /
T40 / T51–T55-facing), so neither reader is forced through the other's
material.

## 2. Intensity normalization

## 3. Effect schema

## 4. AdversaryProfile reference sketch

## 5. Determinism interaction with T27

## 6. Open to revision

## 7. Sources
