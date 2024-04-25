import openai
import discord
import aiohttp
from redbot.core import commands, Config
from redbot.core.bot import Red
from io import BytesIO

class AskChatGPT(commands.Cog):
    """A Redbot cog to interact with OpenAI's ChatGPT and DALL-E."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_global = {
            "api_key": None,
            "model": "gpt-3.5-turbo"
        }
        self.config.register_global(**default_global)

    @commands.command()
    async def generateimage(self, ctx, *, description: str):
        """Generate an image from a description using DALL-E."""
        api_key = await self.config.api_key()
        if not api_key:
            await ctx.send("OpenAI API key is not set. Please set it using `setapikey` command.")
            return
        await self.handle_generateimage(ctx, description)

    @commands.Cog.listener("on_message")
    async def on_mention(self, message: discord.Message):
        if message.author.bot or self.bot.user not in message.mentions:
            return
        content = message.content.replace(f"<@!{self.bot.user.id}>", "").strip()
        content = content.replace(f"<@{self.bot.user.id}>", "").strip()
        await self.handle_askgpt(message, query=content)

    async def handle_askgpt(self, message, *, query: str):
        """Handle the askgpt functionality."""
        api_key = await self.config.api_key()
        if not api_key:
            await message.channel.send("OpenAI API key is not set. Please set it using `setapikey` command.")
            return
        async with message.channel.typing():
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model=await self.config.model(),
                messages=[{"role": "system", "content": "You are a helpful assistant."},
                          {"role": "user", "content": query}]
            )
            full_message = response.choices[0].message["content"]
            for i in range(0, len(full_message), 2000):
                await message.channel.send(full_message[i:i+2000])

    async def handle_generateimage(self, channel, *, description: str):
        """Handle the image generation functionality."""
        api_key = await self.config.api_key()
        if not api_key:
            await channel.send("API key not set.")
            return
        async with channel.typing():
            openai.api_key = api_key
            response = openai.Image.create(prompt=description, n=1)
            image_url = response['data'][0]['url']
            image_data = await self.fetch_image(image_url)
            image = BytesIO(image_data)
            image.seek(0)
            await channel.send(file=discord.File(image, "generated_image.png"))

    async def fetch_image(self, url):
        """Asynchronously fetches an image from a URL using aiohttp."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.read()

async def setup(bot):
    await bot.add_cog(AskChatGPT(bot))

async def teardown(bot):
    await bot.remove_cog("AskChatGPT")
