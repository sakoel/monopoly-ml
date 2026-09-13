"""Agent interface and baseline strategies.

Every agent implements four decisions. Keep this interface stable -- the
learned agent later on just becomes another class here, and then you can
run it head to head against these on identical dice.
"""

from . import board as B

# Rough desirability of each colour group, cheapest first.
# Oranges and light blues score well because of jail proximity;
# greens are expensive to develop relative to their return.
GROUP_VALUE = {
    "brown": 0.7, "lightblue": 1.1, "pink": 1.15, "orange": 1.35,
    "red": 1.2, "yellow": 1.1, "green": 0.95, "darkblue": 1.0,
    "railroad": 1.0, "utility": 0.5,
}


class Agent:
    name = "base"

    def wants_to_buy(self, game, pidx, sq):
        raise NotImplementedError

    def auction_value(self, game, pidx, sq):
        return 0

    def choose_build(self, game, pidx):
        """Return a square to build one house on, or None to stop."""
        return None

    def wants_out_of_jail(self, game, pidx):
        return True


class RandomAgent(Agent):
    name = "random"

    def wants_to_buy(self, game, pidx, sq):
        return game.rng.random() < 0.5

    def auction_value(self, game, pidx, sq):
        return int(B.PRICE[sq] * game.rng.uniform(0.3, 0.8))


class BuyEverythingAgent(Agent):
    """Buys anything affordable, builds on the first legal square."""
    name = "greedy"

    def wants_to_buy(self, game, pidx, sq):
        return True

    def auction_value(self, game, pidx, sq):
        return int(B.PRICE[sq] * 0.7)

    def choose_build(self, game, pidx):
        p = game.players[pidx]
        for sq in game.properties_of(pidx):
            if game.can_build_on(pidx, sq) and p.cash - B.HOUSE_COST[sq] > 0:
                return sq
        return None


class HeuristicAgent(Agent):
    """Keeps a cash buffer, prefers groups it can complete, and pushes to
    three houses on its best monopoly before spreading out."""
    name = "heuristic"

    def __init__(self, reserve=200, group_value=None):
        self.reserve = reserve
        self.gv = group_value or GROUP_VALUE

    def _value(self, game, pidx, sq):
        grp = B.GROUP[sq]
        v = B.PRICE[sq] * self.gv.get(grp, 1.0)
        if grp in B.GROUPS:
            squares = B.GROUPS[grp]
            mine = game.count_owned(pidx, squares)
            others = sum(1 for s in squares
                         if game.owner[s] not in (-1, pidx))
            if mine == len(squares) - 1:
                v *= 2.2               # completes a monopoly
            elif others == len(squares) - 1:
                v *= 1.5               # blocks an opponent's monopoly
            elif mine > 0:
                v *= 1.2
        elif grp == "railroad":
            v *= 1.0 + 0.25 * game.count_owned(pidx, B.RAILROADS)
        return v

    def wants_to_buy(self, game, pidx, sq):
        p = game.players[pidx]
        price = B.PRICE[sq]
        if p.cash - price < self.reserve:
            # still buy if it completes a set
            grp = B.GROUP[sq]
            if grp in B.GROUPS and game.count_owned(pidx, B.GROUPS[grp]) == len(B.GROUPS[grp]) - 1:
                return p.cash >= price
            return False
        return self._value(game, pidx, sq) >= price * 0.8

    def auction_value(self, game, pidx, sq):
        p = game.players[pidx]
        v = self._value(game, pidx, sq)
        cap = max(0, p.cash - self.reserve // 2)
        return int(min(v * 0.9, cap))

    def choose_build(self, game, pidx):
        p = game.players[pidx]
        best, best_score = None, 0.0
        for sq in game.properties_of(pidx):
            if not game.can_build_on(pidx, sq):
                continue
            cost = B.HOUSE_COST[sq]
            if p.cash - cost < self.reserve:
                continue
            h = game.houses[sq]
            # marginal rent gained per dollar spent
            gain = B.RENT[sq][h + 1] - B.RENT[sq][h]
            score = gain / cost
            if h < 3:
                score *= 1.4          # the third house is the big jump
            score *= self.gv.get(B.GROUP[sq], 1.0)
            if score > best_score:
                best, best_score = sq, score
        return best

    def wants_out_of_jail(self, game, pidx):
        # Late game, with many developed properties around, jail is shelter.
        developed = sum(1 for s in B.BUYABLE
                        if game.owner[s] not in (-1, pidx) and game.houses[s] >= 3)
        return developed < 3
