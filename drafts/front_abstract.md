# Abstract

Front matter. Ports into `../thesis-tex/MIT-thesis-template/abstract.tex`
(replace the template's placeholder text). MIT spec: about 500 words or
fewer, no formulas or special characters. This draft is ~380 words.

Structure follows the standard publication abstract — Background, Aim,
Methods, Results, Conclusion (four paragraphs; Background and Aim merged).
Results carry concrete, wiki-traceable numbers; the Conclusion interprets
significance rather than restating them.

Three protocols evaluated (PBFT, Casper FFG, Snowman), matching the locked
three-family scope of the body; the deferred DAG family is not named here.

---

Layer-1 blockchain consensus protocols are proven safe and live under their
stated assumptions, yet deployed networks still halt, stall, and fork when
those assumptions are stretched by real operating conditions. Performance and
security have been studied largely in isolation, and reported numbers come
from different testbeds, workloads, and network topologies, so the field has
no internally consistent basis for comparing protocol families under the same
realistic stress. This thesis quantifies the performance-security tradeoff
across consensus families under matched network-delay and adversarial
conditions.

A single discrete-event simulator hosts simplified implementations of three
representative protocols, one from each of three families: PBFT, Casper FFG,
and Snowman. The three share one metric schema
covering latency, throughput, communication overhead, and consensus
reliability, and are run over a controlled matrix of validator-set sizes,
network-delay distributions, packet-loss levels, and three adversarial
strategies: delayed voting, non-participation, and equivocation. Common random
seeds let the protocols be compared on identical inputs.

No protocol dominates. Communication overhead splits into two regimes: PBFT
and Casper FFG grow linearly with the validator count, while Snowman sits an
order of magnitude higher because of its repeated random subsampling. Under
network delay Snowman is by far the most affected, with its time to finality
rising about twelve to thirteen times its baseline, whereas PBFT and Casper
FFG stay close to theirs. Under packet loss PBFT is the most resilient, the
only protocol still finalizing at twenty percent message loss, and Casper FFG
the most fragile. Under equivocating validators the failure modes diverge:
once the Byzantine fraction passes one third PBFT forks without holding
anyone accountable, Casper FFG keeps safety and makes every offending validator
slashable, and Snowman shows no fork at all. The rankings invert from one
condition to the next, and in every case resilience is bought with added
latency.

Because each family is best on some axis and worst on another, the right
protocol depends on the expected deployment condition rather than on a single
headline benchmark. The thesis contributes a reproducible simulator and
dataset, and a mechanism map that links each protocol's structural design
choice to the failure mode it produces. This map is the like-for-like
comparison the existing literature does not provide.
