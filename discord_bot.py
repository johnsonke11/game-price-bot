import os
import re
import discord
from dotenv import load_dotenv

from agent import agent
from steam_tool import preload_app_list

load_dotenv()

DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip().strip('"').strip("'")

if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_BOT_TOKEN not set. Add it to your .env file: "
        "DISCORD_BOT_TOKEN=your_token_here "
        "(create a bot and copy its token at https://discord.com/developers/applications)"
    )

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

MENTION_PATTERN = re.compile(r"<@!?\d+>")

def _extract_agent_reply(result: dict)-> str:
    """Same content-block handling as the command-prompt version's loop."""
    final_message = result["messages"][-1]
    content = final_message.content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    return content

@client.event
async def on_ready():
    print(f"[debug] Logged in as {client.user} (id={client.user.id})")
    print("[debug] preloading Steam catalog so the first query isn't slow...")
    num_apps = preload_app_list()
    print(f"[debug] loaded {num_apps} apps, ready for queries")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if client.user not in message.mentions:
        return

    user_query = MENTION_PATTERN.sub("",message.content).strip()

    if not(user_query):
        await message.reply("Ask me about a game — e.g. `@me how much is Hades?`")

        return

    async with message.channel.typing():
        try:
            threadconfig = {"configurable": {"thread_id": str(message.author.id)}}
            result = agent.invoke({"messages": [{"role": "user", "content": user_query}]},
                                  config=threadconfig)
            reply_text = _extract_agent_reply(result)
        except Exception as e:
            reply_text = f"Something went wrong looking that up: {e}"

    await message.reply(reply_text)

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
