# Monopoly Simulator + Win Probability Model

A fast, rule-complete Monopoly engine used to (a) answer strategy questions by
Monte Carlo and (b) train a model that estimates each player's win probability
from a board position.

## Validation

The engine was checked against published Monopoly landing statistics before
anything was built on top of it. Over 3,000 simulated games it reproduces:

| result | published | this engine |
|---|---|---|
| most-landed street | Illinois Ave | Illinois Ave (3.08%) |
| best colour group by landing rate | orange | orange (2.88% avg) |
| least-landed streets | Mediterranean / Baltic | Mediterranean (2.04%) |

## Win probability model

367k labelled positions from 4,000 self-play games. Gradient boosting,
**split by game** so positions from a single game never straddle train/test.

| metric | value |
|---|---|
| AUC (all positions) | 0.972 |
| AUC, turns 0-20 | 0.749 |
| AUC, turns 40-60 | 0.977 |
| Brier score | 0.062 |

Well calibrated: positions predicted at 30% win at 36%, positions predicted at
70-80% win at 77%.

Most predictive features: opponents' developed rent (`rent_exposure`), the
player's own rent threat (`rent_potential`), and share of total net worth.

## Monopoly value experiment

Player 0 is granted a colour group at face value, 3,000 paired-seed games,
three heuristic agents. Baseline win rate 0.264.

| group | cost | win rate | edge per $100 |
|---|---|---|---|
| orange | 560 | 0.963 | 0.125 |
| lightblue | 320 | 0.953 | 0.215 |
| pink | 440 | 0.930 | 0.151 |
| darkblue | 750 | 0.765 | 0.067 |
| green | 920 | 0.601 | 0.037 |

Oranges dominate in absolute terms; light blues are the best value; greens and
dark blues underperform their price. This matches the established consensus and
was derived independently.

## Layout

    monopoly/board.py     static board data, card decks
    monopoly/engine.py    rules, turn loop, bankruptcy, auctions
    monopoly/agents.py    strategy interface + baselines
    monopoly/features.py  position -> feature vector
    generate.py           self-play data generation
    train.py              model training and evaluation
    experiment.py         Monte Carlo strategy experiments
    validate.py           landing-frequency correctness check

## Implemented rules

Full 40-square board, doubles and three-doubles-to-jail, complete 16-card
Chance and Community Chest decks, jail (roll / pay / card / three-turn rule),
auctions when a purchase is declined, even-build rule, the 32-house / 12-hotel
bank supply limit including housing shortages, mortgaging, forced liquidation,
and bankruptcy to either a player or the bank.

Not yet implemented: trading.
