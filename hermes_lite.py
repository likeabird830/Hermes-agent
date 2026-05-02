"""
Ultra-lightweight Discord Bot for Render Free Tier
Debug-friendly version with full error output
"""

import os
import sys
import traceback

print("=== HERMES LITE STARTING ===", flush=True)
print(f"Python version: {sys.version}", flush=True)

# Check env vars BEFORE importing anything
for var in ("DISCORD_BOT_TOKEN", "DEEPSEEK_API_KEY", "TAVILY_API_KEY"):
    val = os.environ.get(var, "")
    print(f"{var}: {'SET (' + val[:8] + '...)' if val else 'MISSING!'}", flush=True)

try:
    import asyncio
    print("✓ asyncio imported", flush=True)
    
    import discord
    from discord.ext import commands
    print(f"✓ discord.py v{discord.__version__} imported", flush=True)
    
    import httpx
    print(f"✓ httpx imported", flush=True)
    
except ImportError as e:
    print(f"✗ IMPORT FAILED: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

# ─── Config ────────────────────────────────────
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

if not DISCORD_TOKEN:
    print("FATAL: DISCORD_BOT_TOKEN not set!", flush=True)
    sys.exit(1)
if not DEEPSEEK_API_KEY:
    print("FATAL: DEEPSEEK_API_KEY not set!", flush=True)
    sys.exit(1)

ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "869299535271329872"))
REQUIRE_MENTION = True


# ─── DeepSeek API ──────────────────────────────
async def call_deepseek(messages: list, max_tokens: int = 2048) -> str:
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
            },
        )
        data = resp.json()
        if "error" in data:
            return f"⚠️ DeepSeek Error: {data['error'].get('message', 'unknown')}"
        return data["choices"][0]["message"]["content"]


# ─── Tavily Search ─────────────────────────────
async def tavily_search(query: str, max_results: int = 5) -> str:
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
        result = ""
        if data.get("answer"):
            result = f"📌 **Summary:**\n{data['answer']}\n\n"
        result += "**Sources:**\n"
        for i, item in enumerate(data.get("results", []), 1):
            result += f"{i}. [{item.get('title', 'No title')}]({item.get('url', '')})\n"
        return result


# ─── Message Handler ───────────────────────────
async def handle_message(bot: commands.Bot, message: discord.Message):
    try:
        async with message.channel.typing():
            content = message.content.strip()

            # Remove mention
            for m in [f"<@!{bot.user.id}>", f"<@{bot.user.id}>"]:
                content = content.replace(m, "").strip()

            if not content:
                await message.reply("Hi! 👋 How can I help?")
                return

            # Check for search command
            use_search = False
            lower = content.lower().strip()
            if lower.startswith(("search ", "/search ", "!search ", "搜")):
                use_search = True
                content = content.split(None, 1)[1] if len(content.split()) > 1 else content

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are Hermes, a helpful AI assistant running on Discord. "
                        "You help users with questions, research, coding, and general tasks. "
                        "Be concise but thorough. Respond in the same language the user uses."
                    ),
                }
            ]

            if use_search and TAVILY_API_KEY:
                sr = await tavily_search(content)
                messages.append({"role": "user", "content": f"Search:\n{sr}\n\nQuestion: {content}"})
            else:
                messages.append({"role": "user", "content": content})

            reply = await call_deepseek(messages)

            # Discord 2000 char limit
            if len(reply) <= 2000:
                await message.reply(reply)
            else:
                chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
                await message.reply(chunks[0])
                for chunk in chunks[1:]:
                    await message.channel.send(chunk)

    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        traceback.print_exc()
        try:
            await message.reply(f"❌ Error: `{str(e)[:200]}`")
        except Exception:
            pass


# ─── Bot Setup ─────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name} ({bot.user.id})", flush=True)


@bot.event
async def on_message(message):
    # Ignore own messages
    if message.author.bot:
        return
    # DMs: always respond
    if isinstance(message.channel, discord.DMChannel):
        await handle_message(bot, message)
        return
    # Server: require mention
    if REQUIRE_MENTION:
        if bot.user.id in [m.id for m in message.mentions]:
            await handle_message(bot, message)


# ─── Main ──────────────────────────────────────
print("Starting Hermes Lite...", flush=True)

try:
    bot.run(DISCORD_TOKEN)
except KeyboardInterrupt:
    print("Bot stopped.", flush=True)
except Exception as e:
    print(f"FATAL ERROR: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
