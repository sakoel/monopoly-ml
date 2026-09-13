"""Static board data for the standard US Monopoly edition.

Nothing here mutates during a game. The engine keeps all per-game state
(ownership, houses, mortgages) in flat arrays indexed by square number.
"""

GO = 0
JAIL = 10
FREE_PARKING = 20
GO_TO_JAIL = 30

# Square types
STREET, RAILROAD, UTILITY, TAX, CHANCE, CHEST, CORNER = range(7)

# name, type, price, rent table, house cost, colour group
# rent table for streets: [base, 1h, 2h, 3h, 4h, hotel]
BOARD = [
    ("Go",                  CORNER,   0,   None, 0,   None),
    ("Mediterranean Ave",   STREET,   60,  [2, 10, 30, 90, 160, 250],       50,  "brown"),
    ("Community Chest 1",   CHEST,    0,   None, 0,   None),
    ("Baltic Ave",          STREET,   60,  [4, 20, 60, 180, 320, 450],      50,  "brown"),
    ("Income Tax",          TAX,      0,   200, 0,   None),
    ("Reading RR",          RAILROAD, 200, None, 0,   "railroad"),
    ("Oriental Ave",        STREET,   100, [6, 30, 90, 270, 400, 550],      50,  "lightblue"),
    ("Chance 1",            CHANCE,   0,   None, 0,   None),
    ("Vermont Ave",         STREET,   100, [6, 30, 90, 270, 400, 550],      50,  "lightblue"),
    ("Connecticut Ave",     STREET,   120, [8, 40, 100, 300, 450, 600],     50,  "lightblue"),
    ("Jail",                CORNER,   0,   None, 0,   None),
    ("St. Charles Place",   STREET,   140, [10, 50, 150, 450, 625, 750],    100, "pink"),
    ("Electric Company",    UTILITY,  150, None, 0,   "utility"),
    ("States Ave",          STREET,   140, [10, 50, 150, 450, 625, 750],    100, "pink"),
    ("Virginia Ave",        STREET,   160, [12, 60, 180, 500, 700, 900],    100, "pink"),
    ("Pennsylvania RR",     RAILROAD, 200, None, 0,   "railroad"),
    ("St. James Place",     STREET,   180, [14, 70, 200, 550, 750, 950],    100, "orange"),
    ("Community Chest 2",   CHEST,    0,   None, 0,   None),
    ("Tennessee Ave",       STREET,   180, [14, 70, 200, 550, 750, 950],    100, "orange"),
    ("New York Ave",        STREET,   200, [16, 80, 220, 600, 800, 1000],   100, "orange"),
    ("Free Parking",        CORNER,   0,   None, 0,   None),
    ("Kentucky Ave",        STREET,   220, [18, 90, 250, 700, 875, 1050],   150, "red"),
    ("Chance 2",            CHANCE,   0,   None, 0,   None),
    ("Indiana Ave",         STREET,   220, [18, 90, 250, 700, 875, 1050],   150, "red"),
    ("Illinois Ave",        STREET,   240, [20, 100, 300, 750, 925, 1100],  150, "red"),
    ("B&O RR",              RAILROAD, 200, None, 0,   "railroad"),
    ("Atlantic Ave",        STREET,   260, [22, 110, 330, 800, 975, 1150],  150, "yellow"),
    ("Ventnor Ave",         STREET,   260, [22, 110, 330, 800, 975, 1150],  150, "yellow"),
    ("Water Works",         UTILITY,  150, None, 0,   "utility"),
    ("Marvin Gardens",      STREET,   280, [24, 120, 360, 850, 1025, 1200], 150, "yellow"),
    ("Go To Jail",          CORNER,   0,   None, 0,   None),
    ("Pacific Ave",         STREET,   300, [26, 130, 390, 900, 1100, 1275], 200, "green"),
    ("North Carolina Ave",  STREET,   300, [26, 130, 390, 900, 1100, 1275], 200, "green"),
    ("Community Chest 3",   CHEST,    0,   None, 0,   None),
    ("Pennsylvania Ave",    STREET,   320, [28, 150, 450, 1000, 1200, 1400], 200, "green"),
    ("Short Line RR",       RAILROAD, 200, None, 0,   "railroad"),
    ("Chance 3",            CHANCE,   0,   None, 0,   None),
    ("Park Place",          STREET,   350, [35, 175, 500, 1100, 1300, 1500], 200, "darkblue"),
    ("Luxury Tax",          TAX,      0,   100, 0,   None),
    ("Boardwalk",           STREET,   400, [50, 200, 600, 1400, 1700, 2000], 200, "darkblue"),
]

NAME     = [s[0] for s in BOARD]
KIND     = [s[1] for s in BOARD]
PRICE    = [s[2] for s in BOARD]
RENT     = [s[3] for s in BOARD]
HOUSE_COST = [s[4] for s in BOARD]
GROUP    = [s[5] for s in BOARD]

RAILROAD_RENT = [25, 50, 100, 200]

GROUPS = {}
for i, g in enumerate(GROUP):
    if g and g not in ("railroad", "utility"):
        GROUPS.setdefault(g, []).append(i)

RAILROADS = [i for i, g in enumerate(GROUP) if g == "railroad"]
UTILITIES = [i for i, g in enumerate(GROUP) if g == "utility"]
BUYABLE = [i for i, k in enumerate(KIND) if k in (STREET, RAILROAD, UTILITY)]

# Colour group order around the board, cheapest first
GROUP_ORDER = ["brown", "lightblue", "pink", "orange",
               "red", "yellow", "green", "darkblue"]

# ---------------------------------------------------------------- card decks
# Each card is (code, arg). The engine interprets the codes.
#   move_to      : absolute square, collect $200 if passing Go
#   move_back    : relative squares
#   nearest_rr   : advance to next railroad, pay 2x rent if owned
#   nearest_util : advance to next utility, pay 10x dice if owned
#   goto_jail    : straight to jail, no $200
#   cash         : +/- amount from the bank
#   per_player   : +/- amount collected from / paid to each opponent
#   repairs      : (per_house, per_hotel)
#   jail_card    : keep a get-out-of-jail-free card

CHANCE_DECK = [
    ("move_to", 0),        # Advance to Go
    ("move_to", 24),       # Advance to Illinois Ave
    ("move_to", 11),       # Advance to St. Charles Place
    ("nearest_util", None),
    ("nearest_rr", None),
    ("nearest_rr", None),
    ("cash", 50),          # Bank pays dividend
    ("jail_card", None),
    ("move_back", 3),
    ("goto_jail", None),
    ("repairs", (25, 100)),
    ("cash", -15),         # Speeding fine
    ("move_to", 5),        # Reading Railroad
    ("move_to", 39),       # Boardwalk
    ("per_player", -50),   # Chairman of the board
    ("cash", 150),         # Building loan matures
]

CHEST_DECK = [
    ("move_to", 0),
    ("cash", 200),         # Bank error
    ("cash", -50),         # Doctor's fees
    ("cash", 50),          # Sale of stock
    ("jail_card", None),
    ("goto_jail", None),
    ("cash", 100),         # Holiday fund
    ("cash", 20),          # Income tax refund
    ("per_player", 10),    # Birthday
    ("cash", 100),         # Life insurance
    ("cash", -100),        # Hospital fees
    ("cash", -50),         # School fees
    ("cash", 25),          # Consultancy fee
    ("repairs", (40, 115)),
    ("cash", 10),          # Beauty contest
    ("cash", 100),         # Inheritance
]
