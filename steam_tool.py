import os
import json
import time
import requests
from difflib import get_close_matches
from dotenv import load_dotenv

load_dotenv()

STEAM_KEY = os.environ.get("STEAM_API_KEY","").strip().strip('"').strip("'")
STEAM_APP_LIST_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
STEAM_APP_LIST_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible: game-price-bot/1.0)"}

CACHE_FILE = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_list_cache.json"))
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60 
if STEAM_KEY:
    print(f"[debug] STEAM_API_KEY loaded, length = {len(STEAM_KEY)}")
else:
    print(f"[debug] STEAM_API_KEY is empty or not set")

_app_list_cache = None

def _load_disc_cache() -> list[dict] | None:
    """Return the Cache app list """

    if not os.path.exists(CACHE_FILE):
        return None

    age_seconds = time.time() - os.path.getmtime(CACHE_FILE)
    if age_seconds > CACHE_MAX_AGE_SECONDS:
        print("[debug] disk cache is stale, will refetch from steam")
        return None

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            apps = json.load(f)
        print(f"[DEBUG] loaded {len(apps)} apps from disk cache ({CACHE_FILE})")
        return apps
    except (json.JSONDecodeError, OSError):
        return None
def _save_disc_cache(apps: list[dict]) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(apps, f)
    except OSError as e:
        print(f"[debug] failed to write disk cache: {e}") 

def _get_app_list() -> list[dict]:
    global _app_list_cache
    if _app_list_cache is not None:
        return _app_list_cache

    disk_cached = _load_disc_cache()
    if disk_cached is not None:
        _app_list_cache = disk_cached
        return _app_list_cache

    if not STEAM_KEY:
        raise RuntimeError("STEAM_API_KEY environment variable not set. "
            "Get a free key at https://steamcommunity.com/dev/apikey")

    apps = []
    last_appid = 0
    while True:
        resp = requests.get(
            STEAM_APP_LIST_URL,
            params={
                "key": STEAM_KEY,
                "max_results": 50000,
                "last_appid": last_appid,
                "include_games": True,
                "include_dlc": False,
                "include_software": False,
                "include_videos": False,
                "include_hardware": False,
            },
            headers=REQUEST_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()["response"]
        batch = payload.get("apps", [])
        apps.extend({"appid": a["appid"], "name": a["name"]} for a in batch)
        #print(apps)
        if not payload.get("have_more_results"):
            break
        last_appid = payload["last_appid"]

    _app_list_cache = apps
    _save_disc_cache(apps)
    return _app_list_cache
def get_steam_reviews(game_name: str) -> dict:
    """Look up a game's Steam review summary (score description, totals) by name.
 
    Returns a dict with keys: found (bool), name, review_score_desc,
    total_positive, total_negative, total_reviews. If not found:
    {'found': False, 'query': game_name}.
    """
    result = _find_app_id(game_name)
    if result == None:
        return {"found": False, "query": game_name}

    appid, matched_name = result
    print(f"[debug] matched query {game_name!r} -> {matched_name!r} (appid={appid})")
    resp = requests.get(
        f"https://store.steampowered.com/appreviews/{appid}",
        params={"json": 1, "language": "all", "purchase_type": "all"},
        headers=REQUEST_HEADERS,
        timeout=10,
    )
    

    resp.raise_for_status()
    payload = resp.json()

    if payload.get("success") != 1:
        return {"found": False, "query": game_name}

    summary = payload.get("query_summary", {})

    return {
        "found": True,
        "name": matched_name,
        "review_score_desc": summary.get("review_score_desc"),
        "total_positive": summary.get("total_positive"),
        "total_negative": summary.get("total_negative"),
        "total_reviews": summary.get("total_reviews"),
    }

_TRADEMARK_TRANSLATE = str.maketrans("", "", "\u2122\u00ae\u00a9")  # ™ ® ©

def _normalize(name: str) -> str:
    """Lowercase and strip trademark/copyright symbols so catalog names like
    'DARK SOULS™: REMASTERED' compare cleanly against a plain-typed query
    like 'Dark Souls: Remastered' — without this, the symbol sitting mid-
    string breaks a straightforward prefix/equality comparison entirely.
    """
    return name.strip().lower().translate(_TRADEMARK_TRANSLATE)

def preload_app_list () -> int:
    apps = _get_app_list()
    return len(apps)
def _is_clean_prefix_match(normalized_catalog_name: str, normalized_query: str) -> bool:
    """True if normalized_catalog_name starts with normalized_query AND
    whatever comes right after (ignoring whitespace) is punctuation rather
    than more letters or digits.
 
    This lets "dark souls" correctly match "dark souls: remastered" (once
    trademark symbols are already stripped by _normalize, the next
    character is ':' — a natural boundary) while correctly REJECTING
    "dark souls ii" or "dark souls iii" (the next character is 'i' — a
    letter, meaning this is a distinct, more specific title).
    """
    if not normalized_catalog_name.startswith(normalized_query):
        return False
    remainder = normalized_catalog_name[len(normalized_query):].lstrip()
    if not remainder:
        return True  # nothing left — exact match in disguise
    return not remainder[0].isalnum()

def _find_app_id(game_name: str) -> tuple[int, str] | None:
    apps = _get_app_list()
    query_norm = _normalize(game_name)

    for app in apps:
        if _normalize(app["name"]) == query_norm:
            return app["appid"], app["name"]

    prefix_matches = [
        app for app in apps
        if _is_clean_prefix_match(_normalize(app["name"]), query_norm)
    ]
    if prefix_matches:
        # prefer the shortest matching name — closest to an exact match
        best = min(prefix_matches, key=lambda a: len(a["name"]))
        return best["appid"], best["name"]


    all_names = [app["name"] for app in apps if app["name"].strip()]
    matches = get_close_matches(game_name, all_names, n=1, cutoff=0.6)

    if not matches:
        return None

    matched_name = matches[0]

    for app in apps:
        if app["name"] == matched_name:
            return app["appid"], app["name"]
    return None

def search_steam(game_name: str) -> dict:

    result = _find_app_id(game_name)

    if result == None:
        return {"found": False, "query": game_name}

    app_id, matched_name = result
    print(f"[debug] matched query {game_name!r} -> {matched_name!r} (appid={app_id})")

    resp = requests.get(STEAM_APP_LIST_DETAILS_URL, 
                        params={"appids": app_id, "cc": "us", "l": "en"},
                        timeout=10,)
    resp.raise_for_status()
    payload = resp.json().get(str(app_id), {})

    if not payload.get("success"):
        return {"found": False, "query": game_name}

    data = payload["data"]
    price_overview = data.get("price_overview")
    is_free = data.get("is_free", False)
    release_info = data.get("release_date", {})
    coming_soon = release_info.get("coming_soon", False)
    release_date = release_info.get("date")
    game_name = data.get("name", matched_name)
    price = None if is_free else (price_overview or {}).get("final_formatted")
    discount_percent = (price_overview or {}).get("discount_percent", 0)

    if coming_soon:
        when = release_date or "no confirmed release date yet"
        status_message = f"{game_name} hasn't been released yet. Release: {when}."
    elif is_free:
        status_message = f"{game_name} is free to play on Steam."
    elif price:
        if discount_percent:
            status_message = f"{game_name} is {price} on Steam ({discount_percent}% off)."
        else:
            status_message = f"{game_name} is {price} on Steam."
    else:
        status_message = f"{game_name} is on Steam, but no price is currently listed."



    return {
        "found": True,
        "appid": app_id,
        "name": game_name,
        "genres": [g["description"] for g in data.get("genres", [])],
        "is_free": is_free,
        "price": price,
        "discount_percent": discount_percent,
        "coming_soon": coming_soon,
        "release_date": release_date,
        "status_message": status_message,
    }

if __name__ == "__main__":
    for query in ["Hades","Hollow Knight","asdkfjasdlkfj not a real game"]:
        print(f"\nQuery: {query!r}")
        print(search_steam(query))