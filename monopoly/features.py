"""Turn a board position into a fixed-length feature vector per player.

One row per active player per snapshot. The label is whether that player
went on to win, so a single model learns "given this position, from this
seat, what is my win probability" and you apply it symmetrically to
everyone at the table.

Keeping ratio features (share of total net worth, share of houses) rather
than raw dollars matters: raw cash means something different on turn 10
than on turn 80, but "I hold 60% of the wealth on the board" travels.
"""

from . import board as B

FEATURE_NAMES = [
    "turn", "n_active",
    "cash", "cash_share",
    "net_worth", "nw_share", "nw_rank",
    "n_props", "prop_share",
    "n_monopolies", "n_buildable_monopolies",
    "n_houses", "n_hotels", "house_share",
    "n_railroads", "n_utilities",
    "n_mortgaged", "mortgage_ratio",
    "in_jail", "position",
    "opp_max_nw_share", "opp_monopolies",
    "rent_exposure", "rent_potential",
    "houses_left", "hotels_left",
] + [f"own_{g}" for g in B.GROUP_ORDER]


def _rent_potential(game, pidx):
    """Total rent this player would collect if every opponent landed on
    each of their squares once. A blunt proxy for board threat."""
    total = 0
    for s in game.properties_of(pidx):
        if game.mortgaged[s]:
            continue
        total += game.rent_for(s, 7)
    return total


def extract(game, pidx):
    p = game.players[pidx]
    active = game.active()
    n_active = len(active)

    worths = {q.idx: game.net_worth(q.idx) for q in active}
    total_nw = sum(worths.values()) or 1
    total_cash = sum(q.cash for q in active) or 1
    my_nw = worths.get(pidx, 0)

    props = game.properties_of(pidx)
    total_props = sum(1 for s in B.BUYABLE if game.owner[s] != -1) or 1

    n_houses = sum(game.houses[s] for s in props if game.houses[s] < 5)
    n_hotels = sum(1 for s in props if game.houses[s] == 5)
    all_houses = sum(game.houses[s] for s in B.BUYABLE if game.houses[s] < 5) or 1

    monopolies = [g for g in B.GROUP_ORDER if game.has_monopoly(pidx, g)]
    buildable = [g for g in monopolies
                 if not any(game.mortgaged[s] for s in B.GROUPS[g])]

    opp_nw = [worths[q.idx] for q in active if q.idx != pidx] or [0]
    opp_mono = sum(1 for q in active if q.idx != pidx
                   for g in B.GROUP_ORDER if game.has_monopoly(q.idx, g))

    # what the player could be charged: opponents' developed rent
    exposure = sum(game.rent_for(s, 7) for s in B.BUYABLE
                   if game.owner[s] not in (-1, pidx))

    nw_rank = sorted(worths.values(), reverse=True).index(my_nw) if my_nw in worths.values() else 0

    row = [
        game.turn, n_active,
        p.cash, p.cash / total_cash,
        my_nw, my_nw / total_nw, nw_rank,
        len(props), len(props) / total_props,
        len(monopolies), len(buildable),
        n_houses, n_hotels, n_houses / all_houses,
        game.count_owned(pidx, B.RAILROADS),
        game.count_owned(pidx, B.UTILITIES),
        sum(1 for s in props if game.mortgaged[s]),
        sum(1 for s in props if game.mortgaged[s]) / max(1, len(props)),
        int(p.in_jail), p.pos,
        max(opp_nw) / total_nw, opp_mono,
        exposure, _rent_potential(game, pidx),
        game.houses_left, game.hotels_left,
    ]
    for g in B.GROUP_ORDER:
        sqs = B.GROUPS[g]
        row.append(game.count_owned(pidx, sqs) / len(sqs))
    return row
