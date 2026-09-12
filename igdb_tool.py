import os
import requests

from dotenv import load_dotenv

from igdb_constants import GENRE_NAME_MAP, STORE_TYPE_NAMES

load_dotenv()

CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID","").strip().strip('"').strip("'")
CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET","").strip().strip('"').strip("'")
REQUEST_HEADERS_BASE = {"Accept": "application/json"}

_access_token = None


if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError(
        "TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET not set. Register an app "
        "at https://dev.twitch.tv/console/apps/create and add both to .env"
    )

def get_access_token() -> str:
    global _access_token

    if _access_token is not None:
        return _access_token
    
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET not set. Register an app "
            "at https://dev.twitch.tv/console/apps/create and add both to .env"
        )
    
    resp = requests.post(
        "https://id.twitch.tv/oauth2/token",
        params={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials",

        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def _igdb_query(endpoint: str, body: str):
    token = get_access_token()
    resp = requests.post(
        f"https://api.igdb.com/v4/{endpoint}",
        headers= {
            "Client-ID": CLIENT_ID,
            "Authorization":  f"Bearer {token}"

        },
        data=body,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()

def search_games_by_genre(genre: str,limit: int =5, require_store_link: bool = True,over_fetch_multiplier: int = 4 ) -> dict:
    igdb_genre_name = GENRE_NAME_MAP.get(genre.strip().lower(), genre)
    print(f"[debug] genre search: {genre!r} -> IGDB genre {igdb_genre_name!r}")
    fetch_count = limit * over_fetch_multiplier if require_store_link else limit

    query = (
        f'fields name,total_rating,total_rating_count; '
        f'where genres.name = "{igdb_genre_name}" & total_rating_count > 50; '
        f'sort total_rating desc; '
        f'limit {fetch_count};'
    )
    results = _igdb_query("games",query)


    candidates = [
        {"name": g["name"], "rating": round(g.get("total_rating", 0), 1)}
        for g in results
    ]

    if not require_store_link:
        return candidates[:limit]

    kept = []
    for candidate in candidates:
        links = get_game_store_links(candidate["name"])
        if links:
            candidate["store_links"] = links
            kept.append(candidate)
        if len(kept) >= limit:
            break
    print(f"[debug] genre search kept {len(kept)}/{len(candidates)} candidates "
          f"with confirmed store links")
    return kept

def get_game_store_links(game_name: str) -> dict:
    search_results = _igdb_query("games", 
                                 f'search "{game_name}"; fields id,name,websites.type,websites.url; limit 5;',
                                 )
    if not search_results:
        return {}

    best_game = None
    best_links = {}

    for game in search_results:
        links = {}
        for website in game.get("websites",[]):
            store_name = STORE_TYPE_NAMES.get(website.get("type"))
            url = website.get("url")
            if store_name and url:
                links[store_name] = url
        if len(links) > len(best_links):
            best_game = game
            best_links = links

    if best_game is not None:
        print(f"[debug] matched query {game_name!r} -> {best_game.get('name')!r} "
              f"(igdb_id={best_game.get('id')}, {len(best_links)} store links found)")        
    return best_links

if __name__ == "__main__":
    print("\n--- Genre search: action ---")
    for game in search_games_by_genre("action", limit=5):
        print(game)
 
    print("\n--- Store links: Hollow Knight ---")
    print(get_game_store_links("Hollow Knight"))