"""Head-to-head: ModelAgent vs HeuristicAgent on identical dice."""
import sys, time
from monopoly.engine import Game
from monopoly.agents import HeuristicAgent
from monopoly.model_agent import ModelAgent

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
model = ModelAgent()

def run(agent_factory, label, n=N):
    wins = 0
    t0 = time.time()
    for seed in range(n):
        agents = [agent_factory(), HeuristicAgent(), HeuristicAgent()]
        g = Game(agents, seed=seed, max_turns=200)
        w, _ = g.play()
        wins += (w == 0)
    r = wins/n
    se = (r*(1-r)/n)**0.5
    print(f"{label:22} {r:.3f} +/- {se:.3f}   ({time.time()-t0:.0f}s)")
    return r, se

print(f"{N} games per condition, seat 0 vs two HeuristicAgents\n")
h, hse = run(lambda: HeuristicAgent(), "HeuristicAgent")
m, mse = run(lambda: model, "ModelAgent")
diff = m - h
print(f"\ndifference: {diff:+.3f} +/- {(hse**2+mse**2)**0.5:.3f}")
print(f"model eval calls: {model.calls:,}")