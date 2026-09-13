"""Validate the engine against published Monopoly landing statistics."""
from collections import Counter
from monopoly.engine import Game
from monopoly import board as B
from monopoly.agents import HeuristicAgent

N_GAMES = 3000
totals = [0]*40
for seed in range(N_GAMES):
    g = Game([HeuristicAgent(), HeuristicAgent(), HeuristicAgent()],
             seed=seed, track_landings=True, max_turns=200)
    g.play()
    for i in range(40):
        totals[i] += g.landings[i]

grand = sum(totals)
pct = [100*t/grand for t in totals]

ranked = sorted(range(40), key=lambda i: -pct[i])
print(f"{'square':22} {'%':>6}")
print("-"*30)
for i in ranked[:12]:
    print(f"{B.NAME[i]:22} {pct[i]:6.2f}")
print("...")
for i in ranked[-5:]:
    print(f"{B.NAME[i]:22} {pct[i]:6.2f}")

print("\nBy colour group (mean % per square):")
for grp in B.GROUP_ORDER:
    sqs = B.GROUPS[grp]
    print(f"  {grp:10} {sum(pct[s] for s in sqs)/len(sqs):5.2f}")
rr = sum(pct[s] for s in B.RAILROADS)/4
print(f"  {'railroad':10} {rr:5.2f}")
