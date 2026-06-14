import os
import asyncio
import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "bd")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Guarda sorteos activos en memoria
# Si reinicias el bot, se pierden. Si luego quieres, se puede pasar a JSON o SQLite.
active_giveaways = {}


def parse_duration(duration: str) -> int:
    """
    Convierte un tiempo tipo:
    30s, 10m, 2h, 1d
    a segundos.
    """
    units = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }

    duration = duration.lower().strip()

    if len(duration) < 2:
        raise ValueError("Duración inválida.")

    unit = duration[-1]
    value = duration[:-1]

    if unit not in units:
        raise ValueError("Unidad inválida. Usa s, m, h o d.")

    if not value.isdigit():
        raise ValueError("La cantidad de tiempo debe ser un número.")

    return int(value) * units[unit]


def format_datetime(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M UTC")


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")


@bot.event
async def on_member_join(member: discord.Member):
    if not member.guild.system_channel:
        return

    embed = discord.Embed(
        title="Bienvenido/a",
        description=f"{member.mention}, bienvenido/a a **{member.guild.name}**.",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Miembro #{member.guild.member_count}")

    await member.guild.system_channel.send(embed=embed)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Detecta boost del servidor
    if before.premium_since is None and after.premium_since is not None:
        channel = after.guild.system_channel
        if channel:
            embed = discord.Embed(
                title="Nuevo boost",
                description=f"{after.mention} ha boosteado el servidor. Gracias por el apoyo.",
                color=discord.Color.magenta(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=after.display_avatar.url)
            await channel.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.send(f"Pong. `{round(bot.latency * 1000)}ms`")


@bot.command(name="server")
async def server_info(ctx: commands.Context):
    guild = ctx.guild
    if guild is None:
        await ctx.send("Este comando solo se puede usar en un servidor.")
        return

    owner = guild.owner
    created_at = guild.created_at.strftime("%d/%m/%Y %H:%M UTC")

    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    roles = len(guild.roles)
    boosts = guild.premium_subscription_count or 0
    boost_tier = guild.premium_tier

    embed = discord.Embed(
        title=f"Informacion de {guild.name}",
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc)
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="Owner", value=owner.mention if owner else "Desconocido", inline=True)
    embed.add_field(name="ID", value=str(guild.id), inline=True)
    embed.add_field(name="Creado", value=created_at, inline=False)

    embed.add_field(name="Miembros", value=str(guild.member_count), inline=True)
    embed.add_field(name="Roles", value=str(roles), inline=True)
    embed.add_field(name="Categorias", value=str(categories), inline=True)

    embed.add_field(name="Canales de texto", value=str(text_channels), inline=True)
    embed.add_field(name="Canales de voz", value=str(voice_channels), inline=True)
    embed.add_field(name="Boosts", value=str(boosts), inline=True)

    embed.add_field(name="Nivel boost", value=str(boost_tier), inline=True)
    embed.add_field(name="Verificacion", value=str(guild.verification_level).capitalize(), inline=True)
    embed.add_field(name="AFK Channel", value=guild.afk_channel.mention if guild.afk_channel else "Ninguno", inline=True)

    embed.set_footer(text=f"Solicitado por {ctx.author}", icon_url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)


@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge(ctx: commands.Context, cantidad: int):
    if cantidad < 1:
        await ctx.send("La cantidad debe ser mayor que 0.")
        return

    borrados = await ctx.channel.purge(limit=cantidad + 1)

    aviso = await ctx.send(f"Se borraron **{len(borrados) - 1}** mensajes.")
    await asyncio.sleep(3)
    await aviso.delete()


@purge.error
async def purge_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("No tienes permisos para usar este comando.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Uso correcto: `{PREFIX}purge 10`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Debes poner un numero valido.")
    else:
        await ctx.send("Ocurrio un error al ejecutar ese comando.")


@bot.command(name="gstart")
@commands.has_permissions(manage_guild=True)
async def giveaway_start(ctx: commands.Context, duracion: str, *, premio: str):
    try:
        seconds = parse_duration(duracion)
    except ValueError as e:
        await ctx.send(f"Error: {e}")
        return

    end_time = datetime.now(timezone.utc) + timedelta(seconds=seconds)

    embed = discord.Embed(
        title="Sorteo",
        description=(
            f"**Premio:** {premio}\n"
            f"**Organiza:** {ctx.author.mention}\n"
            f"**Termina:** {format_datetime(end_time)}\n\n"
            f"Reacciona con 🎉 para participar."
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Sorteo activo")

    message = await ctx.send(embed=embed)
    await message.add_reaction("🎉")

    active_giveaways[message.id] = {
        "channel_id": ctx.channel.id,
        "guild_id": ctx.guild.id if ctx.guild else None,
        "prize": premio,
        "end_time": end_time.isoformat()
    }

    await asyncio.sleep(seconds)

    try:
        giveaway_message = await ctx.channel.fetch_message(message.id)
    except discord.NotFound:
        active_giveaways.pop(message.id, None)
        return

    users = []
    for reaction in giveaway_message.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
            break

    active_giveaways.pop(message.id, None)

    if not users:
        await ctx.send(f"El sorteo de **{premio}** termino sin participantes.")
        return

    ganador = random.choice(users)

    end_embed = discord.Embed(
        title="Sorteo finalizado",
        description=(
            f"**Premio:** {premio}\n"
            f"**Ganador:** {ganador.mention}"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    end_embed.set_footer(text="Felicidades")

    await ctx.send(embed=end_embed)


@giveaway_start.error
async def giveaway_start_error(ctx: commands.Context, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("No tienes permisos para iniciar sorteos.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Uso correcto: `{PREFIX}gstart 10m Discord Nitro`")
    else:
        await ctx.send("No se pudo iniciar el sorteo.")


@bot.command(name="help")
async def help_command(ctx: commands.Context):
    embed = discord.Embed(
        title="Comandos del bot",
        color=discord.Color.blurple()
    )
    embed.add_field(name=f"{PREFIX}ping", value="Muestra la latencia del bot.", inline=False)
    embed.add_field(name=f"{PREFIX}server", value="Muestra informacion del servidor.", inline=False)
    embed.add_field(name=f"{PREFIX}purge <cantidad>", value="Borra mensajes del canal.", inline=False)
    embed.add_field(name=f"{PREFIX}gstart <tiempo> <premio>", value="Inicia un sorteo. Ejemplo: bdgstart 10m Nitro", inline=False)

    await ctx.send(embed=embed)


bot.run(TOKEN)
