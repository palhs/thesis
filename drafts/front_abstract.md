# Abstract

Front matter. Ports into `../thesis-tex/MIT-thesis-template/abstract.tex`
(replace the template's placeholder text). MIT spec: about 500 words or
fewer, no formulas or special characters. This draft is ~205 words
(kept short so the supervisor block stays on the abstract page).

Structure follows the standard publication abstract — Background+Aim /
Methods / Results / Conclusion (four paragraphs). Results carry concrete,
wiki-traceable numbers; the Conclusion interprets significance.

Three protocols evaluated (PBFT, Casper FFG, Snowman), matching the locked
three-family scope of the body; the deferred DAG family is not named here.

---

Layer-1 consensus protocols are proven safe and live, yet deployed networks
still halt and fork once conditions drift outside their assumptions. Performance
and security are usually measured on separate harnesses, so protocol families are
rarely compared directly under the same stress. This thesis measures that
tradeoff on one harness.

A discrete-event simulator implements three protocols in simplified form, one per
family: PBFT, Casper FFG, and Snowman. All three share a metric schema and run
under controlled network delay, packet loss, and three adversaries: delayed
voting, non-participation, and equivocation.

No protocol dominates. For PBFT and Casper FFG communication overhead grows
linearly with validator count, whereas for Snowman it runs an order of magnitude
higher. Network delay hurts Snowman most, raising its time to finality twelve to
fifteen times where PBFT roughly doubles and Casper FFG barely moves. Under packet
loss, PBFT proves the most resilient and Casper FFG the most fragile. Past one
third Byzantine, PBFT forks unaccountably, Casper FFG stays safe and slashes
offenders, and Snowman shows no fork.

These are simplified, one-per-family implementations, not a production benchmark,
so protocol choice should follow the expected deployment condition rather than a
single ranking. The thesis contributes a reproducible simulator with its dataset,
and a map from each design choice to the failure it produces.
