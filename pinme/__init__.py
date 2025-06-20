from .pinme import PinMe


async def setup(bot):
    await bot.add_cog(PinMe(bot))
