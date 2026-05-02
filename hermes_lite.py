"""
Lightweight Discord Bot for Render Free Tier
Only features: DeepSeek chat + Tavily web search
Memory footprint: ~80MB (fits in 512MB free tier)
"""

import asyncio
import os
import json
import logging

import discord
from discord.ext import commands
import httpx
import aiohttp

# ─── Config ────────────────────────────────────────────────
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# Must mention bot to trigger response
REQUIRE_MENTION = True
# Your Discord user ID for DM access
ALLOWED_USER_ID = 869299535271329872  # ccl83's ID from config.yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("hermes-lite")


# ─── DeepSeek API ───────────────────────────────────────────
async def call_deepseek(messages: list, max_tokens: int = 2048) -> str:
    """Call DeepSeek chat completion API."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        data = resp.json()
        if "error" in data:
            return f"⚠️ DeepSeek Error: {data['error'].get('message', 'unknown')}"
        return data["choices"][0]["message"]["content"]


# ─── Tavily Search ──────────────────────────────────────────
async def tavily_search(query: str, max_results: int = 5) -> str:
    """Search web via Tavily API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json"},
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "include_answer": True,
            },
        )
        data = resp.json()
        if "answer" in data and data["answer"]:
            result = f"📌 **Summary:**\n{data['answer']}\n\n"
        else:
            result = ""
        result += "**Sources:**\n"
        for i, item in enumerate(data.get("results", []), 1):
            result += f"{i}. [{item.get('title', 'No title')}]({item.get('url', '')})\n"
            if item.get("content"):
                result += f"   {item['content'][:200]}...\n\n"
        return result


# ─── Message Handler ───────────────────────────────────────
def should_respond(message: discord.Message, client_user_id: int) -> bool:
    """Check if we should respond to this message."""
    # Ignore own messages
    if message.author.id == client_user_id:
        return False
    # Always respond to DMs from allowed user
    if isinstance(message.channel, discord.DMChannel):
        return message.author.id == ALLOWED_USER_ID
    # In servers: require mention
    if REQUIRE_MENTION:
        return any(m.id == client_user_id for m in message.mentions)
    return False


async def handle_message(bot: commands.Bot, message: discord.Message):
    """Process an incoming message."""
    try:
        # Show typing indicator
        async with message.channel.typing():
            content = message.content.strip()

            # Remove bot mention from content
            if REQUIRE_MENTION and f"<@!{bot.user.id}>" in content:
                content = content.replace(f"<@!{bot.user.id}>", "").strip()
            elif REQUIRE_MENTION and f"<@{bot.user.id}>" in content:
                content = content.replace(f"<@{bot.user.id}>", "").strip()

            if not content:
                await message.reply("Hi! 👋 How can I help you?")
                return

            # Check if user wants to search
            use_search = False
            search_query = content
            lower_content = content.lower().strip()

            if lower_content.startswith(("search ", "/search ", "!search ", "搜")):
                use_search = True
                search_query = content.split(None, 1)[1] if len(content.split()) > 1 else content

            # Build conversation context
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are Hermes, a helpful AI assistant running on Discord. "
                        "You help users with questions, research, coding, and general tasks. "
                        "Be concise but thorough. Respond in the same language the user uses "
                        "(English or Chinese). You have access to web search when needed."
                    ),
                }
            ]

            # If search requested, do it first
            if use_search:
                search_result = await tavily_search(search_query)
                messages.append(
                    {"role": "user", "content": f"Search results:\n{search_result}\n\nUser question: {search_query}"}
                )
            else:
                messages.append({"role": "user", "content": content})

            # Call DeepSeek
            reply = await call_deepseek(messages)

            # Discord has 2000 char limit per message
            if len(reply) <= 2000:
                await message.reply(reply)
            else:
                # Split long responses
                chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
                await message.reply(chunks[0])
                for chunk in chunks[1:]:
                    await message.channel.send(chunk)

    except Exception as e:
        log.error(f"Error handling message: {e}", exc_info=True)
        try:
            await message.reply(f"❌ Sorry, something went wrong: `{str(e)[:200]}`")
        except Exception:
            pass


# ─── Bot Setup ──────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
)


@bot.event
async def on_ready():
    log.info(f"✅ Logged in as {bot.user.name} ({bot.user.id})")
    log.info(f"🤖 Hermes Lite is online!")


@bot.event
async def on_message(message):
    if should_respond(message, bot.user.id):
        await handle_message(bot, message)


# ─── Health Check for Render ───────────────────────────────
from aiohttp import web

async def health_check(request):
    return web.Response(text="OK", status=200)


async def run_health_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    log.info("🏥 Health check server started on port 10000")


# ─── Main ───────────────────────────────────────────────────
async def main():
    # Validate config
    missing = []
    if not DISCORD_TOKEN:
        missing.append("DISCORD_BOT_TOKEN")
    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")
    if not TAVILY_API_KEY:
        missing.append("TAVILY_API_KEY")

    if missing:
        log.error(f"Missing environment variables: {missing}")
        raise SystemExit(1)

    # Start health check server in background
    asyncio.create_task(run_health_server())

    # Start Discord bot
    await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
