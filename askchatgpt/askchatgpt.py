import os
import discord
import aiohttp
from redbot.core import commands, Config
from redbot.core.bot import Red
from io import BytesIO
from openai import AsyncOpenAI

class AskChatGPT(commands.Cog):
    """A Redbot cog to interact with OpenAI's ChatGPT and DALL-E."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_global(api_key=None)

    @commands.command()
    async def setapikey(self, ctx, *, key: str):
        """Set the OpenAI API key."""
        await self.config.api_key.set(key)
        await ctx.send("API key updated successfully.")

    @commands.command()
    async def generateimage(self, ctx, *, description: str):
        """Generate an image from a description using DALL-E."""
        api_key = await self.config.api_key()
        if not api_key:
            await ctx.send("OpenAI API key is not set. Please set it using `!setapikey` command.")
            return
        
        await self.handle_generateimage(ctx, description, api_key)

    @commands.Cog.listener("on_message")
    async def on_mention(self, message: discord.Message):
        if message.author.bot or self.bot.user not in message.mentions:
            return

        content = message.content.replace(f"<@!{self.bot.user.id}>", "").strip()
        content = content.replace(f"<@{self.bot.user.id}>", "").strip()
        await self.handle_askgpt(message, content)

    async def handle_askgpt(self, message, query: str):
        api_key = await self.config.api_key()
        if not api_key:
            await message.channel.send("OpenAI API key is not set. Please set it using `!setapikey` command.")
            return

        try:
            async with message.channel.typing():
                client = AsyncOpenAI(api_key=api_key)
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": query}],
                    max_tokens=150
                )
                full_message = response.choices[0].message['content'].strip()
                for i in range(0, len(full_message), 2000):
                    await message.channel.send(full_message[i:i+2000])
        except Exception as e:
            await message.channel.send(f"An error occurred: {str(e)}")

    async def handle_generateimage(self, ctx, description: str, api_key: str):
        try:
            async with ctx.typing():
                client = AsyncOpenAI(api_key=api_key)
                response = await client.images.generate(
                    prompt=description,
                    n=1,
                    size="1024x1024"
                )
                image_url = response.data[0].url
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            image_data = await resp.read()
                            image = BytesIO(image_data)
                            image.seek(0)
                            await ctx.send(file=discord.File(image, "generated_image.png"))
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(AskChatGPT(bot))

async def teardown(bot):
    await bot.remove_cog("AskChatGPT")
