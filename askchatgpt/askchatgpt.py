import openai
from redbot.core import commands, Config
from redbot.core.bot import Red

class AskChatGPT(commands.Cog):
    """A Redbot cog to interact with OpenAI's ChatGPT."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_global = {
            "api_key": None,
            "model": "gpt-3.5-turbo"  # Default model
        }
        self.config.register_global(**default_global)

    @commands.command()
    async def askgpt(self, ctx, *, query: str):
        """Ask a question to ChatGPT."""
        api_key = await self.config.api_key()
        model = await self.config.model()
        if not api_key:
            await ctx.send("OpenAI API key is not set. Please set it using `setapikey` command.")
            return

        try:
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "system", "content": "You are a helpful assistant."},
                          {"role": "user", "content": query}]
            )
            message = response.choices[0].message["content"]
            # Check if message is longer than 2000 characters and split if necessary
            if len(message) > 2000:
                for i in range(0, len(message), 2000):
                    await ctx.send(message[i:i+2000])
            else:
                await ctx.send(message)
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
    async def setmodel(self, ctx, new_model: str):
        """Set the OpenAI model (Owner only)."""
        await self.config.model.set(new_model)
        await ctx.send(f"Model updated to {new_model}.")

    @commands.command()
    @commands.is_owner()
    async def getsettings(self, ctx):
        """Get the current settings (Owner only)."""
        api_key = await self.config.api_key()
        model = await self.config.model()
        await ctx.send(f"Current API key: {api_key}\nCurrent model: {model}")

def setup(bot):
    bot.add_cog(AskChatGPT(bot))
