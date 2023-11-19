import openai
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
import asyncio

class ChatGPT(commands.Cog):
    """A Redbot cog to interact with OpenAI's ChatGPT."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_global = {
            "api_key": None
        }
        self.config.register_global(**default_global)

    @commands.command()
    async def askgpt(self, ctx, *, query: str):
        """Ask a question to ChatGPT."""
        api_key = await self.config.api_key()
        if not api_key:
            await ctx.send("OpenAI API key is not set. Please set it using `setapikey` command.")
            return

        try:
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "You are a helpful assistant."},
                          {"role": "user", "content": query}]
            )
            await ctx.send(response.choices[0].message["content"])
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    @commands.is_owner()
    async def setapikey(self, ctx, new_key: str):
        """Set the OpenAI API key (Owner only)."""
        await self.config.api_key.set(new_key)
        await ctx.send("API key updated successfully.")

    @commands.command()
    @commands.is_owner()
    async def getapikey(self, ctx):
        """Get the current OpenAI API key (Owner only)."""
        api_key = await self.config.api_key()
        if api_key:
            await ctx.send(f"The current API key is: {api_key}")
        else:
            await ctx.send("No API key is set.")

def setup(bot):
    bot.add_cog(ChatGPT(bot))
