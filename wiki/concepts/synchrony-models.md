# Network Synchrony Models

Synchrony assumptions govern what a protocol may assume about message
delivery. They are the single most important knob in comparing consensus
algorithms because they determine what the network can do to the protocol in
the worst case.

## The four models

| Model | Assumption on message delay | Representative algorithms |
| :---- | :---- | :---- |
| **Synchronous** | A known upper bound `Δ` on delivery; any message exceeding `Δ` is treated as lost. | Dolev–Strong; classical signed-message BGP; textbook PoW analyses. |
| **Partial synchrony** | Network alternates between synchronous and asynchronous periods; an unknown Global Stabilisation Time (GST) eventually holds with a bounded `Δ` thereafter. | [[algorithms/pbft]], Tendermint, HotStuff, Casper FFG / Gasper. |
| **Asynchronous** | No bound on delivery; messages may be arbitrarily delayed but eventually arrive. | HoneyBadger-BFT, Dumbo, DAG-based ([[algorithms/dag-based]]: Narwhal/Tusk, Bullshark, Mysticeti). |
| **Probabilistic** | No timing assumption required; termination holds with overwhelming probability under random sampling. | [[algorithms/avalanche]] (Snowball/Snowflake/Avalanche), Algorand sortition. |

## Partial synchrony dominates practical BFT

Partial synchrony is the assumption under which most deployed BFT protocols
operate. It is strong enough to sidestep [[concepts/flp-impossibility]]
(after GST, a bounded `Δ` permits deterministic termination) while weak
enough to remain realistic for internet-scale networks (no prior `Δ`
required).

## Simulator requirement

For this thesis, the simulator must support at least:

- **Partial synchrony** — to exercise PBFT-family and PoS-finality fairly.
- **Asynchrony** — to exercise DAG-based protocols fairly.

Avalanche-style protocols remain operable across all models; their
resilience under the same delay distribution becomes a direct basis for
comparison against the other three families.
