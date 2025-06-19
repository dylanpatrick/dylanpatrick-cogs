import os
import discord
import aiohttp
from redbot.core import commands, Config
from redbot.core.bot import Red
from io import BytesIO
from openai import AsyncOpenAI
from collections import defaultdict

class AskChatGPT(commands.Cog):
    """A Redbot cog to interact with OpenAI's ChatGPT and DALL-E with memory and model validation."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_global(api_key=None, model="gpt-3.5-turbo")
        self.memory = defaultdict(list)  # {(channel_id, user_id): [messages]}
        self._model_capability_cache = {}  # For caching validated model info

    @commands.command()
    async def setapikey(self, ctx, *, key: str):
        """Set the OpenAI API key."""
        await self.config.api_key.set(key)
        await ctx.send("API key updated successfully.")

    @commands.command()
    async def setmodel(self, ctx, *, model: str):
        """Set the OpenAI model."""
        await self.config.model.set(model)
        await ctx.send(f"Model updated to {model}.")

    @commands.command()
    async def generateimage(self, ctx, *, description: str):
        """Generate an image from a description using DALL-E."""
        api_key = await self.config.api_key()
        if not api_key:
            await ctx.send("OpenAI API key is not set. Please set it using `!setapikey`.")
            return
        await self.handle_generateimage(ctx, description, api_key)

    @commands.command()
    async def clearmemory(self, ctx):
        """Clear your conversation memory."""
        key = (ctx.channel.id, ctx.author.id)
        if key in self.memory:
            del self.memory[key]
        await ctx.send("Memory cleared for this conversation.")

    @commands.Cog.listener("on_message")
    async def on_mention(self, message: discord.Message):
        if message.author.bot or self.bot.user not in message.mentions:
            return

        content = message.content.replace(f"<@!{self.bot.user.id}>", "").strip()
        content = content.replace(f"<@{self.bot.user.id}>", "").strip()
        await self.handle_askgpt(message, content)

    async def handle_askgpt(self, message, query: str):
        api_key = await self.config.api_key()
        model = await self.config.model()
        if not api_key:
            await message.channel.send("OpenAI API key is not set. Please set it using `!setapikey`.")
            return

        try:
            async with message.channel.typing():
                client = AsyncOpenAI(api_key=api_key)

                key = (message.channel.id, message.author.id)
                history = self.memory[key]
                history.append({"role": "user", "content": query})

                # Determine supported token parameter
                token_param = "max_tokens"
                try:
                    await client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "Test."}],
                        max_completion_tokens=10
                    )
                    token_param = "max_completion_tokens"
                except Exception:
                    pass

                params = {
                    "model": model,
                    "messages": history[-10:],
                    token_param: 1024
                }

                response = await client.chat.completions.create(**params)
                reply = response.choices[0].message.content.strip()

                history.append({"role": "assistant", "content": reply})
                self.memory[key] = history

                await self.send_long_message(message.channel, reply)

        except Exception as e:
            await message.channel.send(f"An error occurred: {str(e)}")

    async def send_long_message(self, channel, content):
        max_length = 2000
        for i in range(0, len(content), max_length):
            await channel.send(content[i:i+max_length])

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
