import os
import discord
import aiohttp
from openai import OpenAI
from redbot.core import commands, Config
from redbot.core.bot import Red
from io import BytesIO

class AskChatGPT(commands.Cog):
    """A Redbot cog to interact with OpenAI's ChatGPT and DALL-E."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_global = {
            "api_key": os.getenv('OPENAI_API_KEY'),  # Get API key from environment variables
            "model": "gpt-3.5-turbo-instruct"  # Updated model
        }
        self.config.register_global(**default_global)
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))  # Initialize the OpenAI client with API key

    @commands.command()
    async def generateimage(self, ctx, *, description: str):
        """Generate an image from a description using DALL-E."""
        if not self.config.api_key:
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
        if not self.config.api_key:
            await message.channel.send("OpenAI API key is not set. Please set it using `setapikey` command.")
            return

        try:
            async with message.channel.typing():
                response = self.client.completions.create(
                    model=await self.config.model(),
                    prompt=query,
                    max_tokens=150,
                    temperature=0.7  # You can adjust the temperature based on how deterministic you want the response to be
                )
                full_message = response.choices[0].text.strip()
                for i in range(0, len(full_message), 2000):
                    await message.channel.send(full_message[i:i+2000])
        except Exception as e:
            await message.channel.send(f"An error occurred: {str(e)}")

    async def handle_generateimage(self, channel, *, description: str):
        if not self.config.api_key:
            await channel.send("API key not set.")
            return

        try:
            async with channel.typing():
                response = self.client.images.create(
                    model="text-to-image-002",  # Updated model
                    prompt=description,
                    n=1
                )
                image_url = response.data[0].url
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
                            image = BytesIO(image_data)
                            image.seek(0)
                            await channel.send(file=discord.File(image, "generated_image.png"))
        except Exception as e:
            await channel.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(AskChatGPT(bot))

async def teardown(bot):
    await bot.remove_cog("AskChatGPT")
