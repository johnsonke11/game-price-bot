import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call
from langgraph.checkpoint.memory import InMemorySaver
from steam_tool import search_steam, preload_app_list, get_steam_reviews
from igdb_tool import search_games_by_genre,get_game_store_links

load_dotenv()

if not os.environ.get("GOOGLE_API_KEY"):
    raise RuntimeError(
        "GOOGLE_API_KEY not set. Add it to your .env file: "
        "GOOGLE_API_KEY=your_key_here "
        "(get a free key, no card required, at https://aistudio.google.com/apikey)"
    )

@tool
def steam_price_lookup(game_name: str) -> dict:
    """Look up a video game's current Steam price, discount, and genres by name.

    Use this whenever the user asks about a specific game's price, whether
    it's on sale, or what genre it is. Pass just the game's name as it would
    appear on Steam (e.g. "Hades", "Hollow Knight").
    """
    print(f"[debug] tool call: steam_price_lookup({game_name!r})")
    result = search_steam(game_name)
    print(f"[debug] tool result: {result}")
    return result

@tool
def steam_reviews_lookup(game_name: str) -> dict:
    """Look up a video game's Steam review summary (e.g. 'Very Positive') by name.
 
    Use this whenever the user asks whether a game is good, well-reviewed,
    or what people think of it. Pass just the game's name as it would
    appear on Steam.
    """
    print(f"[debug] tool call: steam_reviews_lookup({game_name!r})")
    result = get_steam_reviews(game_name)
    print(f"[debug] tool result: {result}")
    return result

@tool
def genre_game_seaerch(genre: str) -> list[dict]:
    """Find well-rated games in a genre (e.g. 'action', 'rpg', 'strategy',
    'shooter', 'platformer', 'puzzle').
 
    Use this when the user asks for game RECOMMENDATIONS or "best/top
    reviewed games" in a category, rather than asking about one specific
    named game. Returns a list of {'name', 'rating'} dicts, best first.
    """
    print(f"[debug] tool call: genre_game_search({genre!r})")
    result = search_games_by_genre(genre)
    print(f"[debug] tool result: {result}")
    return result

@tool
def game_store_links(game_name:str) -> dict:
    """Get direct storefront links (Steam, Nintendo eShop, PlayStation
    Store, GOG) for a specific game by name.
 
    Use this when the user asks WHERE to buy/download a game, or which
    platforms it's available on with a direct link.
    """
    print(f"[debug] tool call: game_store_links({game_name!r})")
    result = get_game_store_links(game_name)
    print(f"[debug] tool result: {result}")
    return result

@wrap_model_call
def force_tool_on_first_turn(request, handler):
    """Force the model to call a tool on the very first turn of a user's
    message, instead of letting it answer from its own (often outdated)
    memorized knowledge. Only the first step is forced — once a tool result
    comes back, the model is free to respond normally with 'auto', so it
    can actually give a final text answer instead of looping forever.
    """
    is_first_step = bool(request.messages) and isinstance(request.messages[-1], HumanMessage)
    if is_first_step:
        request = request.override(tool_choice="any")
    return handler(request)

llm = ChatGoogleGenerativeAI(model ="gemini-3.1-flash-lite", temperature = 0)

tools = [steam_price_lookup],[steam_reviews_lookup]
agent = create_agent(
    model=llm,
    tools=[steam_price_lookup, steam_reviews_lookup, game_store_links, genre_game_seaerch],
    system_prompt=(
        "You are a helpful assistant that answers questions about video "
        "games: Steam prices, discounts, review standing, genre-based "
        "recommendations, and where to buy a game across platforms "
        "(Steam, Nintendo eShop, PlayStation Store, GOG). You have NO "
        "reliable knowledge of current prices, discounts, review scores, "
        "or which games are well-rated in a genre on your own — these "
        "change constantly and any figure or recommendation you recall "
        "from training is very likely wrong or outdated. Use "
        "steam_price_lookup for price/discount/genre questions about ONE "
        "named game, steam_reviews_lookup for whether a specific named "
        "game is good, genre_game_search when the user wants "
        "recommendations or 'best/top' games in a category rather than "
        "asking about a specific title, and game_store_links when the "
        "user asks where to buy/download a game or which platforms it's "
        "on. If a game isn't found, say so clearly rather than guessing. "
        "steam_price_lookup's result includes a 'status_message' field "
        "that already correctly summarizes the price/release situation in "
        "plain English (including unreleased games) — base your answer "
        "on that field rather than re-deriving the situation yourself "
        "from the other fields, since that has proven error-prone. "
        "Keep answers short and conversational. The user may ask "
        "follow-up questions that refer to a game mentioned earlier in "
        "the conversation (e.g. 'what about the sequel') — resolve which "
        "game they mean using conversation history, but still call the "
        "relevant tool fresh rather than reusing an old result from "
        "earlier in the conversation."
    ),
    middleware=[force_tool_on_first_turn],
    checkpointer=InMemorySaver()
)

if __name__ == "__main__":
    print("Loading Steam game catalog...")
    num_apps = preload_app_list()
    print(f"Loaded {num_apps} apps.\n")
    print("Game price chatbot (Steam) — type 'quit' to exit\n")
    threadconfig = {"configurable": {"thread_id": "local-cli-user"}}
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit"}:
            break
        result = agent.invoke({"messages": [{"role": "user", "content": user_input}]},
                              config= threadconfig)
        final_message= result["messages"][-1]
        content = final_message.content
        if isinstance(content,list):
            reply_text = "".join(
                block.get("text", "") for block in content if isinstance(block,dict)
            )
        else:
            reply_text = content
        print(f"\nBot: {reply_text}\n")