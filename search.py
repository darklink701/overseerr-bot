import discord
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env project file 
load_dotenv()

OVERSEERR_API_KEY = os.getenv("OVERSEERR_API_KEY")
OVERSEERR_URL = os.getenv("OVERSEERR_URL")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Discord bot permissions
intents = discord.Intents.default()
intents.message_content = True 

# Create a new instance of the bot and set the command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# Check if the required environment variables are set and print a warning if not
@bot.event
async def on_ready():
    if not OVERSEERR_API_KEY or not OVERSEERR_URL or not DISCORD_BOT_TOKEN:
        print("⚠️ Warning: One or more environment variables are not set. Please check your .env file.")
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("Bot is ready to receive commands!")
    print("------")
# Command to search for movies or TV shows in Overseerr    
@bot.command()
async def search(ctx, *, query: str):

    """Searches for a movie or TV show in Overseerr."""
    headers = {
        "X-Api-Key": OVERSEERR_API_KEY
    }
    params = {
        "query": query
    }

    search_url = f"{OVERSEERR_URL}/api/v1/search"
    response = requests.get(search_url, headers=headers, params=params)

    if response.status_code != 200:
        await ctx.send("❌ Error searching Overseerr.")
        return

    results = response.json().get("results", [])
    if not results:
        await ctx.send("🔍 No results found.")
        return

    # Limit to top 5 results
    limited = results[:5]

    embed = discord.Embed(
        title=f"Search results for: {query}",
        color=discord.Color.blue()
    )

    for item in limited:
        name = item.get("title") or item.get("name")
        media_type = item.get("mediaType")
        release_year = item.get("firstAirDate") or item.get("releaseDate")
        release_year = release_year.split("-")[0] if release_year else "?"
        tmdb_id = item.get("id")
        embed.add_field(
            name=f"{name} ({release_year})",
            value=f"Type: `{media_type}` — TMDb ID: `{tmdb_id}`",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command()
async def login(ctx):
    await ctx.send("🔐 This shit is under construction, bromigo. Ask me for an autograph, or get lost.")
    
    return # Anything below this won't run right now
    redirect_uri = REDIRECT_URI
    login_url = f"{OVERSEERR_URL}/login?redirect={redirect_uri}"

    try:
        await ctx.author.send(f"🔐 Click here to log in to Overseerr via Plex:\n{login_url}")
        await ctx.send("📬 I sent you a DM with the login link. Now say: 'thank you, Johnny.' ")
    except discord.Forbidden:
        await ctx.send("❌ I couldn't DM you. Make sure your DMs are open.")

# Catch-all for command errors, with a Johnny Cage-style response.
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Response for bad or mis-typed command
         await ctx.send("❓ That's not a real command. Try again, or ask Johnny for an autograph.")
    
    else:
        # For other errors:
        print(f"[⚠️] Unhandled command error: {error}")
        await ctx.send("❌ Something broke, but don't blame me. I only break necks.")

# Initialize by invoking the bot with the token from the environment variable
bot.run(DISCORD_BOT_TOKEN)