# Citation keys

The resolver between the wiki's IEEE `[N]` numbering, the biblatex citation
keys used in the LaTeX thesis, and the `wiki/sources/` pages. Every draft
citation ports deterministically through this table: `[N]` is the
wiki-internal cross-reference, the bibkey is the LaTeX `\cite{}` handle, and
the source page holds the full takeaways.

The `.bib` file these keys live in is
`../thesis-tex/MIT-thesis-template/references.bib` (sibling Overleaf repo).
The verbatim IEEE citation strings are owned by
[[concepts/annotated-bibliography]] § "Full IEEE bibliography" — this page
does not duplicate them, only maps the keys.

## Key convention

Format: **`<firstauthor><year><shortname>`**, all lowercase, ASCII only.

- **`<firstauthor>`** — surname of the first listed author, lowercased,
  diacritics and spaces stripped (e.g. `castro`, `amoressesar`). For the
  pseudonymous lead author of [9] ("Team Rocket") use `teamrocket`.
- **`<year>`** — 4-digit publication year.
- **`<shortname>`** — short protocol/topic mnemonic disambiguating the
  entry (e.g. `bgp`, `pbft`, `hotstuff`, `ffg`, `cap`).

Keys are **stable and never renumbered or renamed** — they mirror the
append-only `[N]` policy of [[concepts/annotated-bibliography]]. When a new
source is added, append a new key; do not reuse or mutate existing ones.
The `[N]` label and the bibkey are both permanent and independent: biber
regenerates the printed `[N]` from cite order (`sorting=none`), so the
bibkey is the only thing draft prose hard-codes.

## Entry types

`references.bib` is biblatex (compiled with biber via the MIT template's
`style=ext-numeric-comp`). Three entry types are in use:

- `@article` — journal papers. Required: author, title, journaltitle, year.
- `@inproceedings` — conference papers. Required: author, title, booktitle,
  year.
- `@online` — arXiv preprints. Required: author, title, year, and one of
  url / eprint. Encoded with `eprinttype = {arxiv}`, `eprint = {<id>}`, and
  a derived `url = {https://arxiv.org/abs/<id>}`.

DOIs are intentionally absent from this initial 18-entry build (no
`doi` field on any conference/journal entry). They are a clean,
non-breaking enrichment for a later pass; per the no-invented-citations
rule they were not guessed. The `.bib` is well-formed and compiles without
them.

## Mapping table

| `[N]` | bibkey | type | source page |
|------|--------|------|-------------|
| [1]  | `lamport1982bgp`          | `@article`       | [[sources/2026-04-21_lamport-shostak-pease-bgp-1982]] |
| [2]  | `fischer1985flp`          | `@article`       | [[sources/2026-04-21_flp-impossibility-1985]] |
| [3]  | `dwork1988partialsync`    | `@article`       | [[sources/2026-04-21_dwork-lynch-stockmeyer-partial-sync-1988]] |
| [4]  | `castro1999pbft`          | `@inproceedings` | [[sources/2026-04-21_castro-liskov-pbft-1999]] |
| [5]  | `yin2019hotstuff`         | `@inproceedings` | [[sources/2026-04-21_yin-hotstuff-2019]] |
| [6]  | `buchman2018tendermint`   | `@online`        | [[sources/2026-04-21_buchman-tendermint-2018]] |
| [7]  | `buterin2017casperffg`    | `@online`        | [[sources/2026-04-21_buterin-griffith-casper-ffg-2017]] |
| [8]  | `buterin2020gasper`       | `@online`        | [[sources/2026-04-21_buterin-gasper-2020]] |
| [9]  | `teamrocket2019avalanche` | `@online`        | [[sources/2026-04-21_team-rocket-avalanche-2019]] |
| [10] | `amoressesar2024avalanche`| `@online`        | [[sources/2026-04-21_amores-sesar-avalanche-analysis-2024]] |
| [11] | `danezis2022narwhal`      | `@inproceedings` | [[sources/2026-04-21_danezis-narwhal-tusk-2022]] |
| [12] | `spiegelman2022bullshark` | `@inproceedings` | [[sources/2026-04-21_spiegelman-bullshark-2022]] |
| [13] | `babel2023mysticeti`      | `@online`        | [[sources/2026-04-21_babel-mysticeti-2023]] |
| [14] | `bano2019sok`             | `@inproceedings` | [[sources/2026-04-21_bano-sok-consensus-2019]] |
| [15] | `xiao2020survey`          | `@article`       | [[sources/2026-04-21_xiao-survey-2020]] |
| [16] | `cachin2017wild`          | `@online`        | [[sources/2026-04-21_cachin-vukolic-blockchain-wild-2017]] |
| [17] | `gervais2016powsecurity`  | `@inproceedings` | [[sources/2026-04-21_gervais-pow-security-2016]] |
| [18] | `gilbert2002cap`          | `@article`       | [[sources/2026-05-06_gilbert-lynch-cap-2002]] |
| [19] | `helius2024solanaoutages` | `@online`        | _pending — Backlog (incident postmortems)_ |
| [20] | `monnot2022reorg`         | `@online`        | _pending — Backlog (incident postmortems)_ |
| [21] | `offchainlabs2023finality`| `@online`        | _pending — Backlog (incident postmortems)_ |
| [22] | `cosmos2024v17halt`       | `@online`        | _pending — Backlog (incident postmortems)_ |
| [23] | `sui2024outage`           | `@online`        | _pending — Backlog (incident postmortems)_ |

`[19]–[23]` are production-incident postmortems cited in Chapter 1 §1.2
(the motivation). They are web sources (vendor blogs, foundation forums,
core-dev post-mortems), not peer-reviewed papers, so they are encoded as
`@online` with `url` + `urldate` and **no** `eprint`. Their `wiki/sources/`
pages and verbatim entries in [[concepts/annotated-bibliography]] are a
deferred Researcher task (see `TASKS.md` Backlog); the `.bib` records and
this mapping are added now so Chapter 1 compiles with resolved citations.

## Encoding notes

- **[8] Gasper** — the IEEE entry reads "V. Buterin *et al.*"; encoded as
  `author = {Vitalik Buterin and others}` so biber renders the truncation
  itself rather than hard-coding the literal "et al.".
- **[9] Avalanche** — "Team Rocket" is a pseudonymous lead author; encoded
  as the braced atomic name `{Team Rocket}` followed by the named
  co-authors so biber does not split it into given/family parts.
- Conference `booktitle` strings keep the descriptive venue text (with
  edition/series) from the IEEE citation; year lives in the separate `year`
  field. No `eventdate` / `venue` — the bibliography does not record
  locations.

## Maintenance

This is the initial 18-entry build. As later chapters cite more sources,
the workflow is: ingest the source into `wiki/sources/`, append it to
[[concepts/annotated-bibliography]] with the next `[N]`, mint a bibkey by
the convention above, add the `.bib` record, and append a row here. Keep
this table, the `.bib`, and the annotated bibliography in lockstep.
