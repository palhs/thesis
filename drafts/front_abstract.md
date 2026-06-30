# Abstract

Front matter. Ports into `../thesis-tex/MIT-thesis-template/abstract.tex`
(replace the template's placeholder text). MIT spec: about 500 words or
fewer, no formulas or special characters. This draft is ~245 words
(shortened ~1/3 so the supervisor block stays on the abstract page).

Structure follows the standard publication abstract — Background+Aim /
Methods / Results / Conclusion (four paragraphs). Results carry concrete,
wiki-traceable numbers; the Conclusion interprets significance.

Three protocols evaluated (PBFT, Casper FFG, Snowman), matching the locked
three-family scope of the body; the deferred DAG family is not named here.

---

Layer-1 blockchain consensus protocols are proven safe and live under their
stated assumptions, yet deployed networks still halt, stall, and fork when
those conditions are stretched. Performance and security are usually measured
separately, on different harnesses, so the field lacks a like-for-like
comparison of protocol families under realistic stress. This thesis quantifies
that performance-security tradeoff under matched network-delay and adversarial
conditions.

A single discrete-event simulator hosts simplified implementations of three
protocols, one per family: PBFT, Casper FFG, and Snowman. The three share one
metric schema for latency, throughput, communication overhead, and
reliability, and run under controlled network delay, packet loss, and three
adversarial strategies: delayed voting, non-participation, and equivocation.

No protocol dominates. Communication overhead grows linearly in the validator
count for PBFT and Casper FFG, and is an order of magnitude higher for Snowman,
which polls by repeated random subsampling. Under network delay Snowman is the
most affected, its time to finality rising about twelve to thirteen times,
while the others stay near baseline. Packet loss leaves PBFT the most resilient
and Casper FFG the most fragile. Under equivocation the failure modes diverge:
past one third Byzantine, PBFT forks unaccountably, Casper FFG preserves safety and
makes every offender slashable, and Snowman shows no fork. Rankings invert
across conditions, and resilience is always bought with added latency.

Because each family is best on one axis and worst on another, protocol choice
should follow the expected deployment condition rather than a single benchmark.
The thesis contributes a reproducible simulator and dataset, and a mechanism
map linking each protocol's design choice to the failure mode it produces.
