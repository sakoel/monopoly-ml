"""An agent that decides by asking a trained model to score the position
it would end up in.

This is one-ply lookahead with a learned evaluation function -- the same
shape as a classical chess engine, except the evaluation is learned from
self-play rather than hand-written.

Two things make it fast enough to be usable:

1. Hypothetical positions are produced by mutating game state, extracting
   features, then reverting. Deep-copying the whole Game for every
   candidate move is correct but roughly 50x slower.
2. All candidate moves for one decision are scored in a single
   ``predict_proba`` call. Per-row calls dominate the runtime otherwise.
"""

import numpy as np
import joblib

from . import board as B
from .agents import Agent
from .features import extract


class ModelAgent(Agent):
    name = "model"

    def __init__(self, model_path="model.pkl", margin=0.0, reserve=0):
        blob = joblib.load(model_path)
        self.clf = blob["model"] if isinstance(blob, dict) else blob
        self.margin = margin      # required win-prob gain before acting
        self.reserve = reserve    # hard cash floor, 0 = trust the model
        self.calls = 0

    # ------------------------------------------------------------ scoring
    def _score(self, game, pidx):
        self.calls += 1
        x = np.asarray([extract(game, pidx)], dtype=np.float32)
        return float(self.clf.predict_proba(x)[0, 1])

    def _score_many(self, rows):
        if not rows:
            return np.array([])
        self.calls += len(rows)
        x = np.asarray(rows, dtype=np.float32)
        return self.clf.predict_proba(x)[:, 1]

    # --------------------------------------------------------------- buy
    def wants_to_buy(self, game, pidx, sq):
        p = game.players[pidx]
        price = B.PRICE[sq]
        if p.cash < price + self.reserve:
            return False

        base = extract(game, pidx)

        # hypothetical: we own it and paid for it
        p.cash -= price
        game.owner[sq] = pidx
        bought = extract(game, pidx)
        game.owner[sq] = -1
        p.cash += price

        probs = self._score_many([base, bought])
        return probs[1] > probs[0] + self.margin

    def auction_value(self, game, pidx, sq):
        """Bid up to the point where owning stops improving win probability.
        Probes a few price points rather than solving exactly."""
        p = game.players[pidx]
        if p.cash <= 0:
            return 0
        base_row = extract(game, pidx)
        rows, prices = [base_row], [0]
        game.owner[sq] = pidx
        for frac in (0.3, 0.6, 0.9, 1.2):
            bid = int(B.PRICE[sq] * frac)
            if bid > p.cash:
                break
            p.cash -= bid
            rows.append(extract(game, pidx))
            prices.append(bid)
            p.cash += bid
        game.owner[sq] = -1

        probs = self._score_many(rows)
        best = 0
        for i in range(1, len(probs)):
            if probs[i] > probs[0]:
                best = prices[i]
        return best

    # ------------------------------------------------------------- build
    def choose_build(self, game, pidx):
        p = game.players[pidx]
        cands = [s for s in game.properties_of(pidx)
                 if game.can_build_on(pidx, s)
                 and p.cash - B.HOUSE_COST[s] >= self.reserve]
        if not cands:
            return None

        rows = [extract(game, pidx)]
        for s in cands:
            cost = B.HOUSE_COST[s]
            was_hotel = game.houses[s] == 4
            p.cash -= cost
            if was_hotel:
                game.houses[s] = 5
                game.hotels_left -= 1
                game.houses_left += 4
            else:
                game.houses[s] += 1
                game.houses_left -= 1

            rows.append(extract(game, pidx))

            if was_hotel:
                game.houses[s] = 4
                game.hotels_left += 1
                game.houses_left -= 4
            else:
                game.houses[s] -= 1
                game.houses_left += 1
            p.cash += cost

        probs = self._score_many(rows)
        best_i = int(np.argmax(probs[1:])) + 1
        if probs[best_i] > probs[0] + self.margin:
            return cands[best_i - 1]
        return None

    # -------------------------------------------------------------- jail
    def wants_out_of_jail(self, game, pidx):
        p = game.players[pidx]
        if p.jail_cards > 0:
            return True
        if p.cash < B.PRICE[0] and p.cash < 50:
            return False

        stay = extract(game, pidx)          # still in jail, keep the $50
        p.cash -= 50
        p.in_jail = False
        leave = extract(game, pidx)
        p.in_jail = True
        p.cash += 50

        probs = self._score_many([stay, leave])
        return probs[1] > probs[0]