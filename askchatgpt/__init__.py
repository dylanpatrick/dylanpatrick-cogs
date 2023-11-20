from .chatgpt import ChatGPT


def setup(bot):
    bot.add_cog(AskChatGPT(bot))
