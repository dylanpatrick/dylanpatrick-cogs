# File: pin_cog.py

import discord
from discord.ext.commands import Cog
from redbot.core import commands, Config
from redbot.core.bot import Red
from typing import Union

class PinMe(commands.Cog):
    """Custom pin system that bypasses Discord's native pin limit."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_guild = {"pinned": {}}  # {channel_id: [message_id, ...]}
        self.config.register_guild(**default_guild)

    @commands.group(name="pin", invoke_without_command=True)
    @commands.guild_only()
    async def pin(self, ctx):
        """Custom pin system commands."""
        await ctx.send_help(ctx.command)

    @pin.command(name="add")
    async def pin_add(self, ctx, message: discord.Message):
        """Add a message to the custom pin list."""
        channel_id = str(message.channel.id)
        guild_data = await self.config.guild(ctx.guild).pinned()
        guild_data.setdefault(channel_id, [])

        if message.id in guild_data[channel_id]:
            return await ctx.send("That message is already pinned.")

        guild_data[channel_id].append(message.id)
        await self.config.guild(ctx.guild).pinned.set(guild_data)

        await ctx.send(f"Pinned message: {message.jump_url}")

    @pin.command(name="remove")
    async def pin_remove(self, ctx, message: discord.Message):
        """Remove a message from the custom pin list."""
        channel_id = str(message.channel.id)
        guild_data = await self.config.guild(ctx.guild).pinned()

        if message.id not in guild_data.get(channel_id, []):
            return await ctx.send("That message is not pinned.")

        guild_data[channel_id].remove(message.id)
        await self.config.guild(ctx.guild).pinned.set(guild_data)

        await ctx.send("Message unpinned.")

    @pin.command(name="list")
    async def pin_list(self, ctx):
        """List all pinned messages in this channel."""
        channel_id = str(ctx.channel.id)
        guild_data = await self.config.guild(ctx.guild).pinned()
        message_ids = guild_data.get(channel_id, [])

        if not message_ids:
            return await ctx.send("No pinned messages in this channel.")

        embeds = []
        for msg_id in message_ids:
            try:
                msg = await ctx.channel.fetch_message(msg_id)
                embed = discord.Embed(
                    description=msg.content or "*(No content)*",
                    timestamp=msg.created_at,
                    color=discord.Color.blurple(),
                )
                embed.set_author(name=str(msg.author), icon_url=msg.author.avatar.url if msg.author.avatar else None)
                embed.add_field(name="[Jump to message]", value=f"[Click here]({msg.jump_url})", inline=False)
                embeds.append(embed)
            except discord.NotFound:
                continue

        for embed in embeds:
            await ctx.send(embed=embed)

    @pin.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def pin_clear(self, ctx):
        """Clear all custom pins in this channel."""
        channel_id = str(ctx.channel.id)
        guild_data = await self.config.guild(ctx.guild).pinned()

        if channel_id in guild_data:
            guild_data[channel_id] = []
            await self.config.guild(ctx.guild).pinned.set(guild_data)
            await ctx.send("All pins in this channel have been cleared.")
        else:
            await ctx.send("No pins to clear.")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return

        guild_data = await self.config.guild(message.guild).pinned()
        ch_id = str(message.channel.id)

        if ch_id in guild_data and message.id in guild_data[ch_id]:
            guild_data[ch_id].remove(message.id)
            await self.config.guild(message.guild).pinned.set(guild_data)
