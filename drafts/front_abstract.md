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

No protocol dominates. Communication overhead is linear in validator count for
PBFT and Casper FFG, and an order of magnitude higher for Snowman. Network delay
hurts Snowman most: its time to finality rises twelve to fifteen times, while
PBFT roughly doubles and Casper FFG barely moves. Packet loss leaves PBFT the
most resilient and Casper FFG the most fragile. Past one third Byzantine, PBFT
forks unaccountably, Casper FFG stays safe and slashes offenders, and Snowman
shows no fork.

These are simplified, one-per-family implementations, not a production benchmark,
so protocol choice should follow the expected deployment condition rather than a
single ranking. The thesis contributes a reproducible simulator, its dataset, and
a map from each design choice to the failure it produces.
