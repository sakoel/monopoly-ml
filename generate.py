"""Simulate games, snapshot positions, label with the eventual winner."""
import numpy as np, time, sys
from monopoly.engine import Game
from monopoly.features import extract, FEATURE_NAMES
from monopoly.agents import HeuristicAgent, BuyEverythingAgent, RandomAgent

def make_agents(rng):
    pool = [HeuristicAgent(reserve=rng.choice([100,200,350])),
            BuyEverythingAgent(), HeuristicAgent(reserve=250)]
    return pool

def run(n_games=4000, snap_every=4, seed0=0):
    X, Y, G = [], [], []
    rng = np.random.default_rng(seed0)
    for i in range(n_games):
        agents = make_agents(rng)
        g = Game(agents, seed=seed0+i, max_turns=200)
        rows = []
        turn_mark = -1
        while g.turn < g.max_turns:
            alive = g.active()
            if len(alive) == 1: break
            p = g.players[g.current]
            if not p.bankrupt:
                g.take_turn(p)
            g.current = (g.current + 1) % g.n
            if g.current == 0:
                g.turn += 1
                if g.turn % snap_every == 0 and g.turn != turn_mark:
                    turn_mark = g.turn
                    for q in g.active():
                        rows.append((extract(g, q.idx), q.idx, g.turn))
        alive = g.active()
        winner = alive[0].idx if len(alive)==1 else max(alive, key=lambda q: g.net_worth(q.idx)).idx
        for feats, pidx, t in rows:
            X.append(feats); Y.append(1 if pidx==winner else 0); G.append(i)
        if (i+1) % 500 == 0:
            print(f"  {i+1}/{n_games} games, {len(X)} rows", flush=True)
    return np.array(X, dtype=np.float32), np.array(Y), np.array(G)

if __name__ == "__main__":
    t = time.time()
    X, Y, G = run(int(sys.argv[1]) if len(sys.argv)>1 else 4000)
    np.savez_compressed("data.npz", X=X, Y=Y, G=G, names=np.array(FEATURE_NAMES))
    print(f"{X.shape[0]} rows, {X.shape[1]} features, {time.time()-t:.1f}s")
    print(f"base rate: {Y.mean():.3f}")
