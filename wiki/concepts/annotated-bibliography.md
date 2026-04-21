# Annotated Bibliography

Consolidated IEEE bibliography for the thesis. Every numeric claim in
`drafts/ch*.md` and every `[N]` citation in other wiki pages resolves
through this page; each entry links to a dedicated `wiki/sources/` page
with the full takeaways.

## Citation policy

Fixed rules inherited from the source legend
(`resources/Annotated_Bibliography - Legend & Summary.csv`, row 3):

- **Single consolidated numbering.** The IEEE numeric `[N]` labels used
  here are reused unchanged across every thesis chapter and every wiki
  page. Do not renumber when new sources are added — append.
- **Primary sources for quantitative claims.** Every throughput, latency,
  fault-threshold, or round-count figure in the thesis must be attributed
  to the specific paper that produced it (by IEEE number). Survey papers
  ([14]–[16]) are cited only for taxonomy and framing, never as the source
  of a performance number — the underlying primary paper is cited instead.
- **`TODO(cite)`** marks any claim whose source has not yet been resolved
  through this bibliography. Linter sweeps flag these; see
  `docs/lint-protocol.md`.

Known drift: resolved under S9. The four algorithm pages
[[algorithms/pbft]], [[algorithms/pos]], [[algorithms/avalanche]], and
[[algorithms/dag-based]] previously carried **local** `[1]–[3]` footnote
lists written before this page existed; they now use the consolidated
`[4]–[13]` numbering below, and the per-page `## Sources` blocks have
been collapsed into one-line pointers back here. The sole exception is
a non-bibliography `[ava-docs]` marker on [[algorithms/avalanche]] that
references Ava Labs production documentation for details unavailable in
primary papers; see that page's `## Sources` section for the URL.

## Scope

17 canonical entries covering Layer-1 consensus: foundational distributed-
systems results, protocol papers for the four algorithm families evaluated
in the thesis ([[algorithms/pbft]], [[algorithms/pos]],
[[algorithms/avalanche]], [[algorithms/dag-based]]), surveys supplying
taxonomic framing for [[concepts/consensus-families]], and one empirical-
methodology precedent motivating the simulator-based comparative approach
used here (see [[concepts/problem-statement]] §method).

Category counts: Foundational 3 · Protocol 10 · Survey 3 · Empirical 1.

## Foundational (3)

Theoretical underpinnings every family inherits. All three motivate the
design constraints in [[concepts/quorum-arithmetic]],
[[concepts/synchrony-models]], and [[concepts/flp-impossibility]].

- **[1]** Lamport, Shostak & Pease, *The Byzantine Generals Problem*, ACM
  TOPLAS 4(3), 1982. → [[sources/2026-04-21_lamport-shostak-pease-bgp-1982]].
  Proves deterministic BGP is solvable iff `n ≥ 3f+1` with ≥ `f+1` rounds.
  Establishes the threshold that [[algorithms/pbft]], [[algorithms/pos]],
  and [[algorithms/dag-based]] all inherit.
- **[2]** Fischer, Lynch & Paterson, *Impossibility of Distributed
  Consensus with One Faulty Process*, JACM 32(2), 1985. →
  [[sources/2026-04-21_flp-impossibility-1985]]. No deterministic async
  protocol can guarantee consensus with even one crash fault. Justifies
  every relaxation the thesis studies (partial synchrony, randomness,
  economic incentives).
- **[3]** Dwork, Lynch & Stockmeyer, *Consensus in the Presence of
  Partial Synchrony*, JACM 35(2), 1988. →
  [[sources/2026-04-21_dwork-lynch-stockmeyer-partial-sync-1988]]. Defines
  the partial-synchrony model and proves consensus under `f < n/3`. The
  assumption adopted by PBFT, HotStuff, Tendermint, and Casper FFG.

## Protocol (10)

Primary sources for the four algorithm families. The simulator implements
at least one protocol per family; these pages are the specification
anchors for that implementation.

### PBFT family → [[algorithms/pbft]]

- **[4]** Castro & Liskov, *Practical Byzantine Fault Tolerance*, OSDI
  1999. → [[sources/2026-04-21_castro-liskov-pbft-1999]]. First practical
  three-phase-commit BFT state-machine replication. Canonical baseline
  for the PBFT-family simulator module (T28–T31).
- **[5]** Yin, Malkhi, Reiter, Gueta & Abraham, *HotStuff: BFT Consensus
  with Linearity and Responsiveness*, PODC 2019. →
  [[sources/2026-04-21_yin-hotstuff-2019]]. Linearises view change to
  `O(n)` via threshold signatures; pipelined phases. Optimisation baseline;
  descriptive in the simulator (not separately implemented).
- **[6]** Buchman, Kwon & Milosevic, *The Latest Gossip on BFT
  Consensus* (Tendermint), arXiv:1807.04938, 2018. →
  [[sources/2026-04-21_buchman-tendermint-2018]]. Round-robin leader BFT
  with locking rule; basis of Cosmos SDK chains.

### PoS-finality family → [[algorithms/pos]]

- **[7]** Buterin & Griffith, *Casper the Friendly Finality Gadget*,
  arXiv:1710.09437, 2017. →
  [[sources/2026-04-21_buterin-griffith-casper-ffg-2017]]. BFT finality
  gadget overlaid on a blockchain; accountable safety via slashing.
  Canonical reference for the finality-gadget module.
- **[8]** Buterin et al., *Combining GHOST and Casper* (Gasper),
  arXiv:2003.03052, 2020. → [[sources/2026-04-21_buterin-gasper-2020]].
  LMD-GHOST fork choice + Casper FFG finality; full Ethereum 2 PoS.
  Reference for fork-choice/finality interaction in PoS experiments
  (T34, T54).

### Avalanche family → [[algorithms/avalanche]]

- **[9]** Team Rocket, Yin, Sekniqi, van Renesse & Sirer, *Scalable and
  Probabilistic Leaderless BFT Consensus through Metastability*,
  arXiv:1906.08936, 2019. →
  [[sources/2026-04-21_team-rocket-avalanche-2019]]. Snowflake → Snowball
  → Avalanche cascade; probabilistic BFT via repeated random subsampling.
  Canonical reference for the Avalanche-style simulator module.
- **[10]** Amores-Sesar, Cachin & Schneider, *An Analysis of Avalanche
  Consensus*, arXiv:2401.02811, 2024. →
  [[sources/2026-04-21_amores-sesar-avalanche-analysis-2024]]. Identifies
  conditions under which liveness degrades more than [9] claims. Required
  companion to [9] for a balanced treatment of Avalanche safety/liveness
  in Ch. 2.

### DAG-based family → [[algorithms/dag-based]]

- **[11]** Danezis, Kokoris-Kogias, Sonnino & Spiegelman, *Narwhal and
  Tusk: A DAG-based Mempool and Efficient BFT Consensus*, EuroSys 2022. →
  [[sources/2026-04-21_danezis-narwhal-tusk-2022]]. Decouples data
  availability (DAG mempool) from ordering (consensus). Reference
  implementation target for the DAG module.
- **[12]** Spiegelman, Giridharan, Sonnino & Kokoris-Kogias, *Bullshark:
  DAG BFT Protocols Made Practical*, CCS 2022. →
  [[sources/2026-04-21_spiegelman-bullshark-2022]]. Partially-synchronous
  fast-path DAG BFT with 2-round commit; simpler than Narwhal/Tusk.
- **[13]** Babel, Chursin, Danezis, Kokoris-Kogias & Sonnino, *Mysticeti:
  Reaching the Latency Limits with Uncertified DAGs*, arXiv:2310.14821,
  2023. → [[sources/2026-04-21_babel-mysticeti-2023]]. Uncertified DAG
  consensus at the 3-round BFT latency lower bound; deployed in Sui.
  Upper-bound throughput reference for Ch. 5.

## Survey (3)

Taxonomic framing for Ch. 2; no numeric claim in the thesis cites a survey.

- **[14]** Bano, Sonnino, Al-Bassam, Azouvi, McCorry, Meiklejohn &
  Danezis, *SoK: Consensus in the Age of Blockchains*, AFT 2019. →
  [[sources/2026-04-21_bano-sok-consensus-2019]]. Primary taxonomic anchor
  for [[concepts/consensus-families]] and Ch. 2 literature framing.
- **[15]** Xiao, Zhang, Lou & Hou, *A Survey of Distributed Consensus
  Protocols for Blockchain Networks*, IEEE Commun. Surveys & Tutorials
  22(2), 2020. → [[sources/2026-04-21_xiao-survey-2020]]. Comparative
  metric ranges across families. Pre-dates Narwhal/Tusk/Mysticeti;
  numeric ranges are aggregates, used only as a framing reference.
- **[16]** Cachin & Vukolić, *Blockchain Consensus Protocols in the Wild*,
  arXiv:1707.01873, 2017. →
  [[sources/2026-04-21_cachin-vukolic-blockchain-wild-2017]]. Qualitative
  review of permissioned-chain BFT; methodologically motivates formal
  models and public review.

## Empirical methodology (1)

- **[17]** Gervais, Karame, Wüst, Glykantzis, Ritzdorf & Capkun, *On the
  Security and Performance of Proof of Work Blockchains*, CCS 2016. →
  [[sources/2026-04-21_gervais-pow-security-2016]]. Quantitative PoW
  simulation framework; studies block size and propagation delay against
  throughput and selfish-mining profitability. Methodological precedent
  for the simulation-based, metrics-instrumented comparative approach
  this thesis applies to BFT families (see
  [[concepts/problem-statement]] §method).

## Coverage

All 17 canonical entries `[1]–[17]` have dedicated
[[sources/|source pages]]. S6 created 12 pages (the three foundational
papers [1]–[3], one primary protocol per family plus PBFT-family variants
[4]–[7], [9], [11]–[13], and the principal survey [14]); S9 added the
remaining five ([8], [10], [15]–[17]). Every `[N]` citation used
anywhere in the wiki resolves to an entry above and through to a source
page.

## Full IEEE bibliography

Verbatim IEEE-format citations, for lifting into `drafts/` or for the
final thesis bibliography.

- [1] L. Lamport, R. Shostak, and M. Pease, "The Byzantine Generals
  Problem," *ACM Transactions on Programming Languages and Systems*,
  vol. 4, no. 3, pp. 382–401, 1982.
- [2] M. J. Fischer, N. A. Lynch, and M. S. Paterson, "Impossibility of
  Distributed Consensus with One Faulty Process," *Journal of the ACM*,
  vol. 32, no. 2, pp. 374–382, 1985.
- [3] C. Dwork, N. Lynch, and L. Stockmeyer, "Consensus in the Presence
  of Partial Synchrony," *Journal of the ACM*, vol. 35, no. 2,
  pp. 288–323, 1988.
- [4] M. Castro and B. Liskov, "Practical Byzantine Fault Tolerance," in
  *Proc. 3rd USENIX Symp. Operating Systems Design and Implementation
  (OSDI)*, 1999, pp. 173–186.
- [5] M. Yin, D. Malkhi, M. K. Reiter, G. G. Gueta, and I. Abraham,
  "HotStuff: BFT Consensus with Linearity and Responsiveness," in
  *Proc. ACM Symp. Principles of Distributed Computing (PODC)*, 2019,
  pp. 347–356.
- [6] E. Buchman, J. Kwon, and Z. Milosevic, "The Latest Gossip on BFT
  Consensus," arXiv preprint arXiv:1807.04938, 2018.
- [7] V. Buterin and V. Griffith, "Casper the Friendly Finality Gadget,"
  arXiv preprint arXiv:1710.09437, 2017.
- [8] V. Buterin *et al.*, "Combining GHOST and Casper," arXiv preprint
  arXiv:2003.03052, 2020.
- [9] Team Rocket, M. Yin, K. Sekniqi, R. van Renesse, and E. G. Sirer,
  "Scalable and Probabilistic Leaderless BFT Consensus through
  Metastability," arXiv preprint arXiv:1906.08936, 2019.
- [10] I. Amores-Sesar, C. Cachin, and P. Schneider, "An Analysis of
  Avalanche Consensus," arXiv preprint arXiv:2401.02811, 2024.
- [11] G. Danezis, L. Kokoris-Kogias, A. Sonnino, and A. Spiegelman,
  "Narwhal and Tusk: A DAG-based Mempool and Efficient BFT Consensus,"
  in *Proc. 17th European Conference on Computer Systems (EuroSys)*,
  2022, pp. 34–50.
- [12] A. Spiegelman, N. Giridharan, A. Sonnino, and L. Kokoris-Kogias,
  "Bullshark: DAG BFT Protocols Made Practical," in *Proc. ACM Conf.
  Computer and Communications Security (CCS)*, 2022, pp. 2705–2718.
- [13] K. Babel, A. Chursin, G. Danezis, L. Kokoris-Kogias, and A.
  Sonnino, "Mysticeti: Reaching the Latency Limits with Uncertified
  DAGs," arXiv preprint arXiv:2310.14821, 2023.
- [14] S. Bano, A. Sonnino, M. Al-Bassam, S. Azouvi, P. McCorry, S.
  Meiklejohn, and G. Danezis, "SoK: Consensus in the Age of
  Blockchains," in *Proc. 1st ACM Conf. Advances in Financial
  Technologies (AFT)*, 2019, pp. 183–198.
- [15] Y. Xiao, N. Zhang, W. Lou, and Y. T. Hou, "A Survey of
  Distributed Consensus Protocols for Blockchain Networks," *IEEE
  Communications Surveys & Tutorials*, vol. 22, no. 2, pp. 1432–1465,
  2020.
- [16] C. Cachin and M. Vukolić, "Blockchain Consensus Protocols in the
  Wild," arXiv preprint arXiv:1707.01873, 2017.
- [17] A. Gervais, G. O. Karame, K. Wüst, V. Glykantzis, H. Ritzdorf,
  and S. Capkun, "On the Security and Performance of Proof of Work
  Blockchains," in *Proc. ACM Conf. Computer and Communications
  Security (CCS)*, 2016, pp. 3–16.
