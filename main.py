import os
import asyncio
import random
import json
from datetime import datetime, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "bd")

# =========================
# SERVIDORES PERMITIDOS
# =========================
ALLOWED_GUILD_IDS = [
    1515342135636004977,
    1511755312162668815
]

# =========================
# CONFIG FILE
# =========================
CONFIG_PATH = "config.json"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)

config = load_config()

# guild_id -> role_id
WELCOME_ROLES = config.get("welcome_roles", {})

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


# =========================
# READY
# =========================
@bot.event
async def on_ready():
    print(f"✅ Conectado como {bot.user}")

    for guild in bot.guilds:
        if guild.id not in ALLOWED_GUILD_IDS:
            print(f"❌ Saliendo de {guild.name} ({guild.id})")
            await guild.leave()


# =========================
# COMANDO: SET ROLE
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def setrole(ctx, role: discord.Role):

    if ctx.guild.id not in ALLOWED_GUILD_IDS:
        return

    WELCOME_ROLES[str(ctx.guild.id)] = role.id

    save_config({
        "welcome_roles": WELCOME_ROLES
    })

    await ctx.send(f"✅ Rol de bienvenida configurado: {role.mention}")


# =========================
# WELCOME + AUTO ROLE
# =========================
@bot.event
async def on_member_join(member: discord.Member):

    if member.guild.id not in ALLOWED_GUILD_IDS:
        return

    # ────────────────
    # AUTO ROLE
    # ────────────────
    role_id = WELCOME_ROLES.get(str(member.guild.id))

    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
            except Exception as e:
                print(f"❌ Error dando rol: {e}")

    # ────────────────
    # BIENVENIDA
    # ────────────────
    channel = member.guild.system_channel or discord.utils.get(
        member.guild.text_channels,
        permissions__send_messages=True
    )

    if not channel:
        return

    embed = discord.Embed(
        title="✨ Bienvenido/a al servidor",
        description=(
            f"👋 Hola {member.mention}\n\n"
            f"💜 Bienvenido a **{member.guild.name}**\n"
            f"🌟 Esperamos que disfrutes tu estancia\n\n"
            f"📌 Lee las normas y preséntate"
        ),
        color=discord.Color.from_rgb(120, 80, 255),
        timestamp=datetime.now(timezone.utc)
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    if member.guild.icon:
        embed.set_image(url=member.guild.icon.url)

    embed.set_footer(
        text=f"Eres el miembro #{member.guild.member_count}",
        icon_url=member.guild.icon.url if member.guild.icon else None
    )

    await channel.send(embed=embed)


# =========================
# BOOST EVENT
# =========================
@bot.event
async def on_member_update(before, after):

    if after.guild.id not in ALLOWED_GUILD_IDS:
        return

    if before.premium_since is None and after.premium_since is not None:

        channel = after.guild.system_channel or discord.utils.get(
            after.guild.text_channels,
            permissions__send_messages=True
        )

        if not channel:
            return

        embed = discord.Embed(
            title="🚀 Nuevo Boost!",
            description=(
                f"💜 {after.mention} ha impulsado el servidor\n"
                f"✨ ¡Gracias por el apoyo!"
            ),
            color=discord.Color.purple()
        )

        embed.set_thumbnail(url=after.display_avatar.url)

        await channel.send(embed=embed)


# =========================
# PING
# =========================
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 `{round(bot.latency * 1000)}ms`")


# =========================
# RUN
# =========================
bot.run(TOKEN)

