from redbot.core import commands
import discord
import asyncio

class ValleyRestriction(commands.Cog):
    """Cog to restrict users to post in 'The Valley' for 10 seconds."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def valleyrestrict(self, ctx, member: discord.Member):
        """Restrict a user to post in 'The Valley' for 10 seconds."""
        valley_channel = discord.utils.get(ctx.guild.text_channels, name='The Valley')
        if valley_channel is None:
            await ctx.send("Channel 'The Valley' not found.")
            return

        # Store original permissions
        original_overwrite = valley_channel.overwrites_for(member)

        # Modify permissions to allow sending messages only in 'The Valley'
        overwrite = discord.PermissionOverwrite(send_messages=True)
        await valley_channel.set_permissions(member, overwrite=overwrite)

        # Other channels: deny sending messages
        for channel in ctx.guild.text_channels:
            if channel != valley_channel:
                await channel.set_permissions(member, send_messages=False)

        # Notify and wait for 10 seconds
        await ctx.send(f"{member} is now restricted to 'The Valley' for 10 seconds.")
        await asyncio.sleep(10)

        # Revert permissions
        await valley_channel.set_permissions(member, overwrite=original_overwrite)
        for channel in ctx.guild.text_channels:
            if channel != valley_channel:
                await channel.set_permissions(member, overwrite=None)

        await ctx.send(f"{member} can now post in other channels again.")

def setup(bot):
    bot.add_cog(TheValley(bot))
