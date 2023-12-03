from redbot.core import commands
import discord
import asyncio

class TheValley(commands.Cog):
    """Cog to restrict users to post in 'The Valley' for 10 seconds."""

    def __init__(self, bot):
        self.bot = bot
      
@commands.command()
@commands.has_permissions(manage_roles=True)
async def valleykick(self, ctx, member: discord.Member):
    """Restrict a user to post in 'The Valley' for 10 seconds."""
    valley_channel = discord.utils.get(ctx.guild.text_channels, name='The Valley')
    if valley_channel is None:
        await ctx.send("Channel 'The Valley' not found.")
        return

    # Create a temporary overwrite
    overwrite = discord.PermissionOverwrite()
    overwrite.send_messages = True
    await valley_channel.set_permissions(member, overwrite=overwrite)

    # Reset permissions after 10 seconds
    await asyncio.sleep(10)
    await valley_channel.set_permissions(member, overwrite=None)
    await ctx.send(f"{member} can now post in other channels again.")

def setup(bot):
    bot.add_cog(TheValley(bot))

