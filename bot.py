import os
import urllib.parse
import requests
import discord
import asyncio
import xml.etree.ElementTree as ET
from discord.ext import commands
from dotenv import load_dotenv
import token_store

# ******************* env / config *******************
load_dotenv()

OVERSEERR_API_KEY   = os.getenv("OVERSEERR_API_KEY")
OVERSEERR_URL       = os.getenv("OVERSEERR_URL")
DISCORD_BOT_TOKEN   = os.getenv("DISCORD_BOT_TOKEN")

# Plex device link headers (keep identifiers stable)
PLEX_CLIENT_ID = os.getenv("PLEX_CLIENT_ID", "johnny-cage-bot")
PLEX_PRODUCT   = "JohnnyCageBot"
PLEX_VERSION   = "1.0"
PLEX_DEVICE    = "DiscordBot"
PLEX_PLATFORM  = "Python"

def plex_headers():
    return {
        "Accept": "application/json",
        "X-Plex-Product": PLEX_PRODUCT,
        "X-Plex-Version": PLEX_VERSION,
        "X-Plex-Client-Identifier": PLEX_CLIENT_ID,
        "X-Plex-Device": PLEX_DEVICE,
        "X-Plex-Platform": PLEX_PLATFORM,
    }

# ******************* Bot Pre-Flight Checks/Initialization *******************
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    # make sure DB exists
    token_store.init_db()
    
    # check for missing environmental variables
    missing = [k for k, v in {
        "OVERSEERR_API_KEY": OVERSEERR_API_KEY,
        "OVERSEERR_URL": OVERSEERR_URL,
        "DISCORD_BOT_TOKEN": DISCORD_BOT_TOKEN,
    }.items() if not v]
    
    # Scream if any are missing
    if missing:
        print(f"⚠️ Missing env vars: {', '.join(missing)}")

    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("JOHNNY CAGE IS READY TO ROCK!")
    print("------")

# ******************* COMMANDS *******************

@bot.command()
async def search(ctx, *, query: str):
    """Searches for a movie or TV show in Overseerr."""
    print(f"[DEBUG] Query received: '{query}'")

    encoded_query = urllib.parse.quote(query, safe='')
    search_url = f"{OVERSEERR_URL}/api/v1/search?query={encoded_query}"

    r = requests.get(search_url, headers={"X-Api-Key": OVERSEERR_API_KEY})
    print(f"[DEBUG] Requesting URL: {search_url}")

    if r.status_code != 200:
        await ctx.send("❌ Error searching Overseerr.")
        return

    results = r.json().get("results", [])
    if not results:
        await ctx.send("🔍 No results found.")
        return

    limited = results[:5]
    embed = discord.Embed(title=f"Search results for: {query}", color=discord.Color.blue())

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
    await ctx.send("Am I in any of these? I fucking hope so.")

# Request a movie or TV show by TMDb ID (requires Plex link).
@bot.command()
async def request(ctx, tmdb_id: int):
    """Sends a request to Overseerr for the specified TMDb ID (requires Plex link)."""

    discord_id = str(ctx.author.id)
    if not token_store.get_plex_token(discord_id):
        await ctx.send("🔒 You must `!link` (link your Plex) before requesting.")
        return

    # 1) Figure out mediaType by probing Overseerr's movie/tv endpoints
    headers = {"X-Api-Key": OVERSEERR_API_KEY}
    movie_url = f"{OVERSEERR_URL}/api/v1/movie/{tmdb_id}"
    tv_url    = f"{OVERSEERR_URL}/api/v1/tv/{tmdb_id}"

    movie_resp = await asyncio.to_thread(requests.get, movie_url, headers=headers, timeout=10)
    if movie_resp.status_code == 200:
        media_type = "movie"
    else:
        tv_resp = await asyncio.to_thread(requests.get, tv_url, headers=headers, timeout=10)
        if tv_resp.status_code == 200:
            media_type = "tv"
        else:
            await ctx.send("❌ I couldn’t find that ID as a movie or TV show in Overseerr. Double-check the TMDb ID.")
            return

    # 2) Build correct request body: mediaType + mediaId
    req_headers = {"X-Api-Key": OVERSEERR_API_KEY, "Content-Type": "application/json"}
    payload = {"mediaType": media_type, "mediaId": tmdb_id}
    req_url = f"{OVERSEERR_URL}/api/v1/request"

    r = await asyncio.to_thread(requests.post, req_url, headers=req_headers, json=payload, timeout=15)

    if r.status_code == 201:
        await ctx.send(f"🥊 Requested **{media_type}** with TMDb `{tmdb_id}`. Johnny approves.")
    elif r.status_code == 409:
        await ctx.send("🕶️ Already requested. Even Johnny doesn’t do reruns.")
    else:
        # surface any error message Overseerr returns
        try:
            detail = r.json()
        except Exception:
            detail = r.text[:200]
        await ctx.send(f"💥 Request failed (status {r.status_code}). {detail}")

# Link your Plex account to enable requests.
@bot.command(name="link")
async def link(ctx):
    """Link your Plex account (device code flow via v1 XML)."""
    import xml.etree.ElementTree as ET  # local import to avoid messing with your globals

    # Use XML for the v1 endpoints
    XML_HEADERS = dict(plex_headers())
    XML_HEADERS["Accept"] = "application/xml"

    # 1) Create PIN (v1 XML)
    create_url = "https://plex.tv/pins.xml"
    r = await asyncio.to_thread(requests.post, create_url, headers=XML_HEADERS, timeout=10)
    if r.status_code != 201:
        await ctx.send("❌ Could not start Plex linking. Try again.")
        return

    root = ET.fromstring(r.text)  # <Pin ...> or <pin>...</pin>
    pin_id     = root.attrib.get("id")         or root.findtext("id")
    code       = root.attrib.get("code")       or root.findtext("code")
    expires_in = root.attrib.get("expiresIn")  or root.findtext("expiresIn") or "120"

    if not pin_id or not code:
        snippet = r.text[:300].replace("\n", " ")
        await ctx.send(f"❌ Unexpected response from Plex. (debug): `{snippet}`")
        return

    expires_in = int(expires_in)

    # 2) DM the user the short code
    try:
        await ctx.author.send(
            f"🔗 **Plex Link**\n"
            f"Go to https://plex.tv/link and enter this code:\n\n"
            f"**`{code}`**\n\n"
            f"You have ~{expires_in} seconds."
        )
        await ctx.send("📬 I DM’d you a Plex link code.")
    except discord.Forbidden:
        await ctx.send("❌ I couldn't DM you. Open your DMs and run `!link` again.")
        return

    # 3) Poll for auth token (v1 XML)
    status_url = f"https://plex.tv/pins/{pin_id}.xml"
    deadline = asyncio.get_event_loop().time() + expires_in
    plex_token = None
    last_xml = ""

    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(3)
        g = await asyncio.to_thread(requests.get, status_url, headers=XML_HEADERS, timeout=10)
        if g.status_code != 200:
            continue
        last_xml = g.text
        sr = ET.fromstring(g.text)

        # Handle different shapes/keys Plex may return
        plex_token = (
            sr.attrib.get("authToken") or
            sr.attrib.get("auth_token") or
            sr.findtext("authToken") or
            sr.findtext("auth_token")
        )
        if plex_token:
            break

    if not plex_token:
        snippet = last_xml[:300].replace("\n", " ")
        await ctx.author.send(f"⌛ Link timed out or token not found. (debug): `{snippet}`")
        return

    # 4) Save Plex token for this Discord user
    token_store.save_plex_token(str(ctx.author.id), plex_token)
    await ctx.author.send("✅ Plex linked! You can now make requests.")
    
# Unlink your Plex account.
@bot.command()
async def unlink(ctx):
    """Remove your Plex link."""
    token_store.delete_plex_token(str(ctx.author.id))
    await ctx.send("🔓 Your Plex link has been removed.")

# ******************* ERROR HANDLING/VERBOSITY/STDOUT *******************
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❓ What the fuck, dude? Try again, or ask me for an autograph.")
    else:
        print(f"[⚠️] Unhandled command error: {error}")
        await ctx.send("❌ Something broke, but don't blame me. I only break necks.")

# ******************* run *******************
bot.run(DISCORD_BOT_TOKEN)
