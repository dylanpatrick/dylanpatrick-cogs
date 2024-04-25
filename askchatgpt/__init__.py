from .askchatgpt import AskChatGPT


async def setup(bot):
    await bot.add_cog(AskChatGPT(bot))
