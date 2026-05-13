# Adversary Model

## 1. Framing and scope

Design contract for the catalog of adversarial behaviours the simulator
admits across the four-protocol scope (PBFT, Casper FFG, Snowman,
Narwhal+Tusk). This page is the **catalog** — generic capability ×
protocol matrix (§§2–6) and protocol-specific attack surfaces (§7).
Runtime obligations (intensity normalization, effect schema,
`AdversaryProfile` reference sketch, T27 determinism) are in
[[concepts/adversary-model-runtime]]. Split per `docs/wiki-spec.md`
§ Page size; precedent: [[concepts/network-model]] /
[[concepts/network-model-phases]], [[concepts/simulation-design]] /
[[concepts/simulation-design-runtime]].

The catalog is organised in two layers. **Layer one** — generic
capability × protocol matrix: `delay-emission`, `withhold-participation`,
`equivocate-vote`, `disrupt-leader`, bound per-protocol with one
structural `N/A` and one noted reduction. **Layer two** —
protocol-specific surface: three attacks each rooted in a property only
one family exhibits. The catalog is **static-only**: an
`AdversaryProfile` is data, not behaviour; kind, intensity, node set,
and per-kind config are fixed at sim-start. Matches the static half of
[[concepts/fault-model]] and pins the determinism contract in
[[concepts/adversary-model-runtime]] §5. Intensity is denominated in
each protocol's **natural fault-threshold unit**: PBFT and Narwhal+Tusk
in replicas; Casper FFG in stake; Snowman in validators (full mapping
in [[concepts/adversary-model-runtime]] §2). Attachment is owned by
[[concepts/node-model#adversary-attachment]] (`self.adversary` slot +
per-protocol FSM touchpoint matrix); this page owns binding semantics
per cell. Effect columns reuse [[concepts/evaluation-metrics]].

## 2. Generic capability × protocol matrix

## 3. delay-emission

## 4. withhold-participation

## 5. equivocate-vote

## 6. disrupt-leader

## 7. Protocol-specific surfaces

## 8. Revisions

## 9. Sources
