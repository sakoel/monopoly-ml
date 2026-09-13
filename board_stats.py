"""Per-square metrics for the visualization."""
import json
from monopoly.engine import Game
from monopoly import board as B
from monopoly.agents import HeuristicAgent

N = 4000
totals = [0]*40
for seed in range(N):
    g = Game([HeuristicAgent(), HeuristicAgent(), HeuristicAgent()],
             seed=seed, track_landings=True, max_turns=200)
    g.play()
    for i in range(40):
        totals[i] += g.landings[i]
grand = sum(totals)
land = [100*t/grand for t in totals]

out = []
for i in range(40):
    kind = B.KIND[i]
    d = {"i": i, "name": B.NAME[i], "group": B.GROUP[i],
         "price": B.PRICE[i], "land": round(land[i], 3),
         "kind": ["street","rr","util","tax","chance","chest","corner"][kind]}
    if kind == B.STREET:
        rents = B.RENT[i]
        hc = B.HOUSE_COST[i]
        d["rents"] = rents
        d["houseCost"] = hc
        # expected rent per 100 opponent rolls, at 0 / 3 houses / hotel
        p = land[i]/100
        d["ev0"]  = round(p*rents[0]*2*100, 1)   # monopoly, undeveloped
        d["ev3"]  = round(p*rents[3]*100, 1)
        d["ev5"]  = round(p*rents[5]*100, 1)
        # rolls to repay the cost of getting to 3 houses
        cost3 = B.PRICE[i] + 3*hc
        d["payback3"] = round(cost3 / (p*rents[3]), 1) if rents[3] else None
        d["cost3"] = cost3
    elif kind == B.RAILROAD:
        d["rents"] = B.RAILROAD_RENT
        d["ev3"] = round(land[i]/100*100*100, 1)
    json_safe = {k:(v if v is not None else None) for k,v in d.items()}
    out.append(json_safe)

groupstats = {
 "orange":{"cost":560,"win":0.963,"edge":0.699},
 "lightblue":{"cost":320,"win":0.953,"edge":0.689},
 "pink":{"cost":440,"win":0.930,"edge":0.666},
 "red":{"cost":680,"win":0.860,"edge":0.596},
 "railroad":{"cost":800,"win":0.856,"edge":0.592},
 "yellow":{"cost":800,"win":0.795,"edge":0.531},
 "darkblue":{"cost":750,"win":0.765,"edge":0.501},
 "brown":{"cost":120,"win":0.674,"edge":0.410},
 "green":{"cost":920,"win":0.601,"edge":0.337},
}
for k,v in groupstats.items():
    v["perDollar"] = round(100*v["edge"]/v["cost"], 3)

print(json.dumps({"squares":out,"groups":groupstats,"baseline":0.264}))
