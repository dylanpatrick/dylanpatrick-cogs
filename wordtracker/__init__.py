from .wordtracker import WordTracker


def setup(bot):
    bot.add_cog(WordTracker(bot))
