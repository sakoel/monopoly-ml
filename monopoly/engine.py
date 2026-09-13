"""Monopoly game engine.

Design notes
------------
* All per-game state lives in flat lists indexed by square (0-39) or by
  player index. No object churn in the inner loop -- this needs to run
  hundreds of thousands of games.
* Every game takes an explicit ``random.Random``, so any result is
  reproducible from its seed. This matters enormously once you start
  comparing agents: you want the same dice for both sides.
* Agents never touch state directly. They receive the ``Game`` and return
  decisions. That keeps the rules in one place and makes it impossible for
  an agent to cheat by accident.
"""

import random
from . import board as B

MAX_HOUSES = 32
MAX_HOTELS = 12
JAIL_FINE = 50
GO_SALARY = 200
DEFAULT_START_CASH = 1500


class Player:
    __slots__ = ("idx", "cash", "pos", "in_jail", "jail_turns",
                 "jail_cards", "bankrupt", "agent")

    def __init__(self, idx, agent, cash):
        self.idx = idx
        self.agent = agent
        self.cash = cash
        self.pos = 0
        self.in_jail = False
        self.jail_turns = 0
        self.jail_cards = 0
        self.bankrupt = False


class Game:
    def __init__(self, agents, seed=None, start_cash=DEFAULT_START_CASH,
                 max_turns=500, track_landings=False):
        self.rng = random.Random(seed)
        self.players = [Player(i, a, start_cash) for i, a in enumerate(agents)]
        self.n = len(agents)

        self.owner = [-1] * 40          # -1 = unowned / not buyable
        self.houses = [0] * 40          # 0-4 houses, 5 = hotel
        self.mortgaged = [False] * 40

        self.houses_left = MAX_HOUSES
        self.hotels_left = MAX_HOTELS

        self.chance = list(range(16))
        self.chest = list(range(16))
        self.rng.shuffle(self.chance)
        self.rng.shuffle(self.chest)
        self.chance_i = 0
        self.chest_i = 0

        self.turn = 0
        self.max_turns = max_turns
        self.current = 0
        self.winner = None
        self.landings = [0] * 40 if track_landings else None
        self.last_roll = 7

    # ------------------------------------------------------------- helpers
    def active(self):
        return [p for p in self.players if not p.bankrupt]

    def group_owner(self, group):
        """Return the player index owning every square in a group, else -1."""
        squares = B.GROUPS.get(group)
        if squares is None:
            return -1
        first = self.owner[squares[0]]
        if first == -1:
            return -1
        for s in squares[1:]:
            if self.owner[s] != first:
                return -1
        return first

    def has_monopoly(self, pidx, group):
        return self.group_owner(group) == pidx

    def count_owned(self, pidx, squares):
        return sum(1 for s in squares if self.owner[s] == pidx)

    def properties_of(self, pidx):
        return [s for s in B.BUYABLE if self.owner[s] == pidx]

    def net_worth(self, pidx):
        """Cash plus liquidation value. Mortgaged land counts at nothing extra."""
        total = self.players[pidx].cash
        for s in self.properties_of(pidx):
            if not self.mortgaged[s]:
                total += B.PRICE[s]
            else:
                total += B.PRICE[s] // 2
            total += self.houses[s] * B.HOUSE_COST[s]
        return total

    # --------------------------------------------------------------- money
    def _liquid_potential(self, p):
        """Cash the player could raise without going bankrupt."""
        total = p.cash
        for s in self.properties_of(p.idx):
            total += self.houses[s] * (B.HOUSE_COST[s] // 2)
            if not self.mortgaged[s]:
                total += B.PRICE[s] // 2
        return total

    def _raise_cash(self, p, target):
        """Sell houses and mortgage until cash >= target, or nothing is left."""
        # Sell houses first (agents can override the order later).
        while p.cash < target:
            best = None
            for s in self.properties_of(p.idx):
                if self.houses[s] > 0:
                    # keep the even-build rule intact when selling
                    grp = B.GROUPS[B.GROUP[s]]
                    if self.houses[s] >= max(self.houses[q] for q in grp):
                        if best is None or B.HOUSE_COST[s] > B.HOUSE_COST[best]:
                            best = s
            if best is None:
                break
            self._sell_house(p.idx, best)

        while p.cash < target:
            candidates = [s for s in self.properties_of(p.idx)
                          if not self.mortgaged[s] and self.houses[s] == 0]
            if not candidates:
                break
            s = min(candidates, key=lambda x: B.PRICE[x])
            self.mortgaged[s] = True
            p.cash += B.PRICE[s] // 2
        return p.cash >= target

    def pay(self, payer_idx, amount, creditor_idx=None):
        """Move money. Handles forced liquidation and bankruptcy."""
        p = self.players[payer_idx]
        if amount <= 0:
            return
        if p.cash < amount:
            self._raise_cash(p, amount)
        if p.cash >= amount:
            p.cash -= amount
            if creditor_idx is not None:
                self.players[creditor_idx].cash += amount
        else:
            self._bankrupt(payer_idx, creditor_idx)

    def _sell_house(self, pidx, sq):
        if self.houses[sq] == 5:
            self.houses[sq] = 4
            self.hotels_left += 1
            self.houses_left -= 4
            # if the bank has no houses to give back, the hotel is razed
            if self.houses_left < 0:
                self.houses_left += 4
                self.houses[sq] = 0
                self.players[pidx].cash += 5 * (B.HOUSE_COST[sq] // 2)
                return
        else:
            self.houses[sq] -= 1
            self.houses_left += 1
        self.players[pidx].cash += B.HOUSE_COST[sq] // 2

    def _bankrupt(self, pidx, creditor_idx):
        p = self.players[pidx]
        p.bankrupt = True
        # Raze all buildings back to the bank
        for s in self.properties_of(pidx):
            if self.houses[s] == 5:
                self.hotels_left += 1
                self.houses[s] = 0
            elif self.houses[s] > 0:
                self.houses_left += self.houses[s]
                self.houses[s] = 0
        if creditor_idx is not None and not self.players[creditor_idx].bankrupt:
            c = self.players[creditor_idx]
            c.cash += max(0, p.cash)
            c.jail_cards += p.jail_cards
            for s in self.properties_of(pidx):
                self.owner[s] = creditor_idx
        else:
            for s in self.properties_of(pidx):
                self.owner[s] = -1
                self.mortgaged[s] = False
        p.cash = 0
        p.jail_cards = 0

    # ---------------------------------------------------------------- rent
    def rent_for(self, sq, dice_total, multiplier=1):
        owner = self.owner[sq]
        if owner == -1 or self.mortgaged[sq]:
            return 0
        kind = B.KIND[sq]
        if kind == B.STREET:
            h = self.houses[sq]
            base = B.RENT[sq][h]
            if h == 0 and self.has_monopoly(owner, B.GROUP[sq]):
                base *= 2
            return base * multiplier
        if kind == B.RAILROAD:
            owned = self.count_owned(owner, B.RAILROADS)
            return B.RAILROAD_RENT[owned - 1] * multiplier
        if kind == B.UTILITY:
            owned = self.count_owned(owner, B.UTILITIES)
            rate = 10 if (owned == 2 or multiplier == 10) else 4
            return rate * dice_total
        return 0

    # ---------------------------------------------------------- board flow
    def _advance_to(self, p, target, collect_go=True):
        if collect_go and target < p.pos:
            p.cash += GO_SALARY
        p.pos = target

    def _goto_jail(self, p):
        p.pos = B.JAIL
        p.in_jail = True
        p.jail_turns = 0

    def _draw(self, deck_name):
        if deck_name == "chance":
            card = B.CHANCE_DECK[self.chance[self.chance_i]]
            self.chance_i = (self.chance_i + 1) % 16
        else:
            card = B.CHEST_DECK[self.chest[self.chest_i]]
            self.chest_i = (self.chest_i + 1) % 16
        return card

    def _apply_card(self, p, code, arg, dice_total):
        if code == "move_to":
            self._advance_to(p, arg)
            self._resolve_square(p, dice_total)
        elif code == "move_back":
            p.pos = (p.pos - arg) % 40
            self._resolve_square(p, dice_total)
        elif code == "goto_jail":
            self._goto_jail(p)
        elif code == "cash":
            if arg >= 0:
                p.cash += arg
            else:
                self.pay(p.idx, -arg)
        elif code == "per_player":
            for q in self.active():
                if q.idx == p.idx:
                    continue
                if arg >= 0:
                    self.pay(q.idx, arg, p.idx)
                else:
                    self.pay(p.idx, -arg, q.idx)
        elif code == "jail_card":
            p.jail_cards += 1
        elif code == "repairs":
            per_house, per_hotel = arg
            cost = 0
            for s in self.properties_of(p.idx):
                if self.houses[s] == 5:
                    cost += per_hotel
                else:
                    cost += self.houses[s] * per_house
            self.pay(p.idx, cost)
        elif code == "nearest_rr":
            target = min((r for r in B.RAILROADS if r > p.pos), default=B.RAILROADS[0])
            self._advance_to(p, target)
            self._land_on_owned(p, dice_total, multiplier=2)
        elif code == "nearest_util":
            target = min((u for u in B.UTILITIES if u > p.pos), default=B.UTILITIES[0])
            self._advance_to(p, target)
            self._land_on_owned(p, dice_total, multiplier=10)

    def _land_on_owned(self, p, dice_total, multiplier=1):
        sq = p.pos
        owner = self.owner[sq]
        if owner == -1:
            self._offer_purchase(p, sq)
        elif owner != p.idx:
            rent = self.rent_for(sq, dice_total, multiplier)
            if rent:
                self.pay(p.idx, rent, owner)

    def _offer_purchase(self, p, sq):
        price = B.PRICE[sq]
        if p.cash >= price and p.agent.wants_to_buy(self, p.idx, sq):
            p.cash -= price
            self.owner[sq] = p.idx
        else:
            self._auction(sq)

    def _auction(self, sq):
        """Simple ascending auction. Each agent names a max; highest pays
        one dollar over the runner-up (a second-price style settlement,
        which is close to how a real ascending auction terminates)."""
        bids = []
        for p in self.active():
            cap = min(p.cash, p.agent.auction_value(self, p.idx, sq))
            if cap > 0:
                bids.append((cap, p.idx))
        if not bids:
            return
        bids.sort(reverse=True)
        top_bid, winner = bids[0]
        second = bids[1][0] if len(bids) > 1 else 1
        price = min(top_bid, second + 1)
        self.players[winner].cash -= price
        self.owner[sq] = winner

    def _resolve_square(self, p, dice_total):
        sq = p.pos
        if self.landings is not None:
            self.landings[sq] += 1
        kind = B.KIND[sq]
        if kind in (B.STREET, B.RAILROAD, B.UTILITY):
            self._land_on_owned(p, dice_total)
        elif kind == B.TAX:
            self.pay(p.idx, B.RENT[sq])
        elif kind == B.CHANCE:
            code, arg = self._draw("chance")
            self._apply_card(p, code, arg, dice_total)
        elif kind == B.CHEST:
            code, arg = self._draw("chest")
            self._apply_card(p, code, arg, dice_total)
        elif sq == B.GO_TO_JAIL:
            self._goto_jail(p)

    # ---------------------------------------------------------- build phase
    def can_build_on(self, pidx, sq):
        if B.KIND[sq] != B.STREET:
            return False
        grp = B.GROUP[sq]
        if not self.has_monopoly(pidx, grp):
            return False
        squares = B.GROUPS[grp]
        if any(self.mortgaged[s] for s in squares):
            return False
        if self.houses[sq] >= 5:
            return False
        # even build: cannot exceed the minimum in the group
        if self.houses[sq] > min(self.houses[s] for s in squares):
            return False
        if self.houses[sq] == 4:
            return self.hotels_left > 0
        return self.houses_left > 0

    def build(self, pidx, sq):
        p = self.players[pidx]
        cost = B.HOUSE_COST[sq]
        if p.cash < cost or not self.can_build_on(pidx, sq):
            return False
        p.cash -= cost
        if self.houses[sq] == 4:
            self.houses[sq] = 5
            self.hotels_left -= 1
            self.houses_left += 4      # four houses return to the bank
        else:
            self.houses[sq] += 1
            self.houses_left -= 1
        return True

    def _build_phase(self, p):
        for _ in range(10):           # cap the work per turn
            sq = p.agent.choose_build(self, p.idx)
            if sq is None or not self.build(p.idx, sq):
                break
        # opportunistic unmortgaging
        for s in self.properties_of(p.idx):
            if self.mortgaged[s]:
                cost = int(B.PRICE[s] * 0.55)
                if p.cash - cost > 300:
                    p.cash -= cost
                    self.mortgaged[s] = False

    # ---------------------------------------------------------------- turn
    def _roll(self):
        a = self.rng.randint(1, 6)
        b = self.rng.randint(1, 6)
        return a, b

    def take_turn(self, p):
        if p.bankrupt:
            return
        doubles = 0
        while True:
            d1, d2 = self._roll()
            total = d1 + d2
            self.last_roll = total
            is_double = d1 == d2

            if p.in_jail:
                if self._handle_jail(p, is_double, total):
                    return          # stayed in jail, turn over
                # got out via doubles -> move, but no extra roll
                self._advance_to(p, (p.pos + total) % 40)
                self._resolve_square(p, total)
                break

            if is_double:
                doubles += 1
                if doubles == 3:
                    self._goto_jail(p)
                    return

            self._advance_to(p, (p.pos + total) % 40)
            self._resolve_square(p, total)

            if p.bankrupt or not is_double:
                break

        if not p.bankrupt:
            self._build_phase(p)

    def _handle_jail(self, p, is_double, total):
        """Return True if the player is still in jail and the turn ends."""
        p.jail_turns += 1
        if is_double:
            p.in_jail = False
            p.jail_turns = 0
            return False
        wants_out = p.agent.wants_out_of_jail(self, p.idx)
        if wants_out and p.jail_cards > 0:
            p.jail_cards -= 1
            p.in_jail = False
            p.jail_turns = 0
        elif wants_out and p.cash >= JAIL_FINE:
            self.pay(p.idx, JAIL_FINE)
            p.in_jail = False
            p.jail_turns = 0
        elif p.jail_turns >= 3:
            self.pay(p.idx, JAIL_FINE)
            p.in_jail = False
            p.jail_turns = 0
        else:
            return True
        self._advance_to(p, (p.pos + total) % 40)
        self._resolve_square(p, total)
        return True   # movement already resolved; no extra roll

    # ---------------------------------------------------------------- play
    def play(self, snapshot_every=0, snapshot_fn=None):
        """Run to completion. Returns the winning player index, or None on a
        turn-limit draw (resolved by net worth)."""
        snapshots = []
        while self.turn < self.max_turns:
            alive = self.active()
            if len(alive) == 1:
                self.winner = alive[0].idx
                break
            p = self.players[self.current]
            if not p.bankrupt:
                self.take_turn(p)
                if snapshot_every and self.turn % snapshot_every == 0 and snapshot_fn:
                    snapshots.append(snapshot_fn(self))
            self.current = (self.current + 1) % self.n
            if self.current == 0:
                self.turn += 1
        if self.winner is None:
            alive = self.active()
            self.winner = max(alive, key=lambda q: self.net_worth(q.idx)).idx
        return self.winner, snapshots


def play_game(agents, seed=None, **kwargs):
    g = Game(agents, seed=seed, **kwargs)
    winner, _ = g.play()
    return winner, g
