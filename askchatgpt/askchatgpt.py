import openai
import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from io import BytesIO

class ChatGPT(commands.Cog):
    """A Redbot cog to interact with OpenAI's ChatGPT and DALL-E."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_global = {
            "api_key": None,
            "model": "gpt-3.5-turbo"  # Default model
        }
        self.config.register_global(**default_global)

    @commands.command()
    async def generateimage(self, ctx, *, description: str):
        """Generate an image from a description using DALL-E."""
        # ... generateimage command implementation ...

    @commands.Cog.listener("on_message")
    async def on_mention(self, message: discord.Message):
        """Handle messages that mention the bot."""
        if message.author.bot or self.bot.user not in message.mentions:
            return

        content = message.content.replace(f"<@!{self.bot.user.id}>", "").strip()

        # Handling the askgpt functionality when the bot is mentioned
        await self.handle_askgpt(message, query=content)

    async def handle_askgpt(self, message, *, query: str):
        """Handle the askgpt functionality."""
        api_key = await self.config.api_key()
        model = await self.config.model()
        if not api_key:
            await message.channel.send("OpenAI API key is not set. Please set it using `setapikey` command.")
            return

        try:
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "system", "content": "You are a helpful assistant."},
                          {"role": "user", "content": query}]
            )
            await message.channel.send(response.choices[0].message["content"])
        except Exception as e:
            await message.channel.send(f"An error occurred: {str(e)}")

    # ... rest of your cog ...

def setup(bot):
    bot.add_cog(ChatGPT(bot))
