import os
import json
import asyncio
import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "bd")

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# =========================
# GIVEAWAYS STORAGE
# =========================
DATA_FILE = "giveaways.json"

def load_giveaways():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_giveaways(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

active_giveaways = load_giveaways()


# =========================
# UTILS
# =========================
def parse_duration(duration: str) -> int:
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}

    duration = duration.lower().strip()
    if len(duration) < 2:
        raise ValueError("Duración inválida")

    unit = duration[-1]
    value = duration[:-1]

    if unit not in units:
        raise ValueError("Usa s, m, h o d")

    if not value.isdigit():
        raise ValueError("Debe ser número")

    return int(value) * units[unit]


def format_time(dt: datetime):
    return dt.strftime("%d/%m/%Y %H:%M UTC")


async def get_welcome_channel(member: discord.Member):
    guild = member.guild

    return (
        guild.system_channel
        or discord.utils.get(guild.text_channels, permissions__send_messages=True)
    )


# =========================
# EVENTS
# =========================
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")


@bot.event
async def on_member_join(member: discord.Member):
    channel = await get_welcome_channel(member)
    if not channel:
        return

    embed = discord.Embed(
        title="👋 Bienvenido",
        description=f"{member.mention} se ha unido a **{member.guild.name}**",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Miembros: {member.guild.member_count}")

    await channel.send(embed=embed)


@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        channel = await get_welcome_channel(after)
        if not channel:
            return

        embed = discord.Embed(
            title="🚀 Nuevo Boost",
            description=f"{after.mention} ha boosteado el servidor ❤️",
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=after.display_avatar.url)

        await channel.send(embed=embed)


# =========================
# COMMANDS
# =========================
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 `{round(bot.latency * 1000)}ms`")


@bot.command()
async def server(ctx):
    g = ctx.guild

    embed = discord.Embed(
        title=f"📊 {g.name}",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(name="👑 Owner", value=g.owner.mention if g.owner else "N/A")
    embed.add_field(name="👥 Miembros", value=g.member_count)
    embed.add_field(name="💬 Canales", value=len(g.channels))
    embed.add_field(name="🎭 Roles", value=len(g.roles))
    embed.add_field(name="🚀 Boosts", value=g.premium_subscription_count)

    if g.icon:
        embed.set_thumbnail(url=g.icon.url)

    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount <= 0:
        return await ctx.send("Número inválido")

    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Eliminados {len(deleted)-1} mensajes")

    await asyncio.sleep(3)
    await msg.delete()


# =========================
# GIVEAWAYS SYSTEM (NO BLOCKING)
# =========================
async def finish_giveaway(message_id: str, channel_id: int, guild_id: int, prize: str, seconds: int):
    await asyncio.sleep(seconds)

    guild = bot.get_guild(guild_id)
    if not guild:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        return

    try:
        msg = await channel.fetch_message(int(message_id))
    except:
        return

    users = []

    for reaction in msg.reactions:
        if str(reaction.emoji) == "🎉":
            async for u in reaction.users():
                if not u.bot:
                    users.append(u)

    if not users:
        await channel.send(f"❌ Sorteo de **{prize}** sin participantes")
        return

    winner = random.choice(users)

    embed = discord.Embed(
        title="🎉 Sorteo Finalizado",
        description=f"🏆 Premio: **{prize}**\n👑 Ganador: {winner.mention}",
        color=discord.Color.green()
    )

    await channel.send(embed=embed)

    active_giveaways.pop(message_id, None)
    save_giveaways(active_giveaways)


@bot.command()
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, duration: str, *, prize: str):
    try:
        seconds = parse_duration(duration)
    except Exception as e:
        return await ctx.send(f"❌ {e}")

    end_time = datetime.now(timezone.utc) + timedelta(seconds=seconds)

    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=(
            f"🏆 **{prize}**\n"
            f"👤 Host: {ctx.author.mention}\n"
            f"⏰ Termina: {format_time(end_time)}\n\n"
            f"Reacciona 🎉 para participar"
        ),
        color=discord.Color.gold()
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    active_giveaways[str(msg.id)] = {
        "channel_id": ctx.channel.id,
        "guild_id": ctx.guild.id,
        "prize": prize,
        "end": end_time.isoformat()
    }

    save_giveaways(active_giveaways)

    asyncio.create_task(
        finish_giveaway(str(msg.id), ctx.channel.id, ctx.guild.id, prize, seconds)
    )


# =========================
# HELP
# =========================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📚 Comandos",
        color=discord.Color.blurple()
    )

    embed.add_field(name="bdping", value="Latencia del bot", inline=False)
    embed.add_field(name="bdserver", value="Info del servidor", inline=False)
    embed.add_field(name="bdpurge <n>", value="Borrar mensajes", inline=False)
    embed.add_field(name="bdgstart <tiempo> <premio>", value="Sorteo", inline=False)

    await ctx.send(embed=embed)


# =========================
# RUN BOT
# =========================
bot.run(TOKEN)
