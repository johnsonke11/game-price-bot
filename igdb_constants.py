"""
Static mapping data for igdb_tool.py — kept separate from the API logic so
the tool file reads as "what this does" rather than being interrupted by
large lookup tables.
"""
 
# Confirmed by directly querying IGDB's /genres endpoint — IGDB has NO
# plain "Action" genre; its taxonomy is more granular than Steam/RAWG.
# Mapping common casual terms to IGDB's real genre names. Unrecognized
# input is passed through as-is by the caller (in case someone types an
# exact IGDB genre name directly, e.g. "Turn-based strategy (TBS)").
GENRE_NAME_MAP = {
    "action": "Adventure",  # closest real IGDB genre — see project notes
    "action-adventure": "Adventure",
    "action adventure": "Adventure",
    "adventure": "Adventure",
    "rpg": "Role-playing (RPG)",
    "role-playing": "Role-playing (RPG)",
    "shooter": "Shooter",
    "strategy": "Strategy",
    "platformer": "Platform",
    "platform": "Platform",
    "fighting": "Fighting",
    "puzzle": "Puzzle",
    "racing": "Racing",
    "sports": "Sport",
    "sport": "Sport",
    "simulation": "Simulator",
    "simulator": "Simulator",
    "indie": "Indie",
    "visual novel": "Visual Novel",
    "tactical": "Tactical",
    "hack and slash": "Hack and slash/Beat 'em up",
    "beat em up": "Hack and slash/Beat 'em up",
    "point and click": "Point-and-click",
    "moba": "MOBA",
    "card game": "Card & Board Game",
    "board game": "Card & Board Game",
    "arcade": "Arcade",
    "pinball": "Pinball",
    "quiz": "Quiz/Trivia",
    "trivia": "Quiz/Trivia",
    "rts": "Real Time Strategy (RTS)",
    "tbs": "Turn-based strategy (TBS)",
}
 
# Confirmed empirically by querying a real multi-platform game (Hollow
# Knight) and inspecting the raw "websites" field — see igdb_explore.py.
# Only these codes are confirmed; others (Epic, Xbox Store, App Store)
# weren't present in that sample and aren't included here to avoid
# guessing at unconfirmed values.
STORE_TYPE_NAMES = {
    13: "Steam",
    17: "GOG",
    23: "PlayStation Store",
    24: "Nintendo eShop",
}
 