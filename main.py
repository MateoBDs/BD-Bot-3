import os
import asyncio
import random
from datetime import datetime, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "bd")
ALLOWED_GUILD_IDS = [
    1515342135636004977,
    1511755312162668815
]

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
# WELCOME (MEJORADO)
# =========================
@bot.event
async def on_member_join(member: discord.Member):

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
    embed.set_image(url=member.guild.icon.url if member.guild.icon else discord.Embed.Empty)

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
# SERVER INFO (ESTILO DASHBOARD)
# =========================
@bot.command()
async def server(ctx):
    g = ctx.guild

    owner = g.owner
    created = g.created_at.strftime("%d/%m/%Y")

    text = len(g.text_channels)
    voice = len(g.voice_channels)
    roles = len(g.roles)

    boosts = g.premium_subscription_count or 0
    level = g.premium_tier

    embed = discord.Embed(
        title=f"📊 Dashboard de {g.name}",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )

    if g.icon:
        embed.set_thumbnail(url=g.icon.url)

    embed.add_field(
        name="👑 Propietario",
        value=owner.mention if owner else "Desconocido",
        inline=True
    )

    embed.add_field(name="🆔 ID", value=g.id, inline=True)
    embed.add_field(name="📅 Creado", value=created, inline=True)

    embed.add_field(name="👥 Miembros", value=g.member_count, inline=True)
    embed.add_field(name="🎭 Roles", value=roles, inline=True)
    embed.add_field(name="🚀 Boosts", value=boosts, inline=True)

    embed.add_field(name="📈 Nivel Boost", value=level, inline=True)
    embed.add_field(name="💬 Canales texto", value=text, inline=True)
    embed.add_field(name="🔊 Canales voz", value=voice, inline=True)

    embed.add_field(
        name="🔐 Verificación",
        value=str(g.verification_level).capitalize(),
        inline=True
    )

    embed.add_field(
        name="😴 AFK",
        value=g.afk_channel.mention if g.afk_channel else "No configurado",
        inline=True
    )

    embed.set_footer(
        text=f"Solicitado por {ctx.author}",
        icon_url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)


# =========================
# PURGE
# =========================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):

    if amount <= 0:
        return await ctx.send("❌ Número inválido")

    deleted = await ctx.channel.purge(limit=amount + 1)

    msg = await ctx.send(f"🧹 Eliminados **{len(deleted)-1}** mensajes")
    await asyncio.sleep(3)
    await msg.delete()


# =========================
# GIVEAWAY SIMPLE
# =========================
@bot.command()
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, duration: str, *, prize: str):

    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}

    try:
        time = int(duration[:-1]) * units[duration[-1]]
    except:
        return await ctx.send("❌ Usa formato: 10m, 1h, 30s")

    embed = discord.Embed(
        title="🎉 SORTEO ACTIVO",
        description=(
            f"🏆 Premio: **{prize}**\n"
            f"👤 Host: {ctx.author.mention}\n\n"
            f"Reacciona 🎉 para participar"
        ),
        color=discord.Color.gold()
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(time)

    msg = await ctx.channel.fetch_message(msg.id)

    users = []
    for r in msg.reactions:
        if str(r.emoji) == "🎉":
            async for u in r.users():
                if not u.bot:
                    users.append(u)

    if not users:
        return await ctx.send("❌ No hubo participantes")

    winner = random.choice(users)

    end = discord.Embed(
        title="🏆 Sorteo Finalizado",
        description=f"🎉 Ganador: {winner.mention}\n🏆 Premio: **{prize}**",
        color=discord.Color.green()
    )

    await ctx.send(embed=end)


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
    embed.add_field(name="bdpurge", value="Borrar mensajes", inline=False)
    embed.add_field(name="bdgstart", value="Sorteos", inline=False)

    await ctx.send(embed=embed)

# =========================
# BOOST EVENT (PRIVADO)
# =========================
@bot.event
async def on_member_update(before, after):

    if after.guild.id not in ALLOWED_GUILD_IDS:
        return

    if before.premium_since is None and after.premium_since is not None:
        
# =========================
# RUN
# =========================
bot.run(TOKEN)
