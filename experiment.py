"""Which monopoly is actually worth the most?

Player 0 starts with a given colour group, paid for at face value out of
starting cash so the comparison is fair. Same seeds across every
condition -- paired sampling kills most of the dice variance.
"""
import numpy as np
from monopoly.engine import Game
from monopoly import board as B
from monopoly.agents import HeuristicAgent

N = 3000
results = {}
for grp in B.GROUP_ORDER + ["railroad"]:
    sqs = B.GROUPS[grp] if grp in B.GROUPS else B.RAILROADS
    cost = sum(B.PRICE[s] for s in sqs)
    wins = 0
    for seed in range(N):
        g = Game([HeuristicAgent(), HeuristicAgent(), HeuristicAgent()],
                 seed=seed, max_turns=200)
        for s in sqs:
            g.owner[s] = 0
        g.players[0].cash -= cost          # pay face value
        w, _ = g.play()
        wins += (w == 0)
    rate = wins/N
    se = (rate*(1-rate)/N)**0.5
    results[grp] = (rate, se, cost)

base_wins = sum(Game([HeuristicAgent(),HeuristicAgent(),HeuristicAgent()],
                     seed=s, max_turns=200).play()[0]==0 for s in range(N))/N
print(f"baseline win rate (no gift): {base_wins:.3f}\n")
print(f"{'group':11}{'cost':>6}{'win rate':>11}{'edge':>9}{'per $100':>10}")
print("-"*47)
for grp,(r,se,c) in sorted(results.items(), key=lambda kv:-kv[1][0]):
    edge = r - base_wins
    print(f"{grp:11}{c:>6}{r:>8.3f}±{se:.3f}{edge:>+9.3f}{100*edge/c:>10.3f}")
