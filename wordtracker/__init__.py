from .wordtracker import WordTracker


async def setup(bot):
    await bot.add_cog(WordTracker(bot))
