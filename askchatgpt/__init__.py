from .askchatgpt import AskChatGPT


def setup(bot):
    bot.add_cog(AskChatGPT(bot))
