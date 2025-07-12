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

# Initialize the bot with the command prefix
intents = discord.Intents.default()
intents.message_content = True 

# Create a new instance of the bot
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

# Initialize by invoking the bot with the token from the environment variable
bot.run(DISCORD_BOT_TOKEN)