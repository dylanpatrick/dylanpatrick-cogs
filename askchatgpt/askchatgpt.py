import os
import discord
import aiohttp
from redbot.core import commands, Config
from redbot.core.bot import Red
from io import BytesIO
from openai import AsyncOpenAI
from collections import defaultdict
import json

MAX_MEMORY_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB

class AskChatGPT(commands.Cog):
    """A Redbot cog to interact with OpenAI's ChatGPT and DALL-E with memory and model validation."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_global(api_key=None, model="gpt-4o", memory={})
        self.memory = defaultdict(list)  # {guild_id: [messages]}

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
    async def clearmemory(self, ctx):
        """Clear your conversation memory for the server."""
        guild_id = str(ctx.guild.id if ctx.guild else ctx.channel.id)
        if guild_id in self.memory:
            del self.memory[guild_id]
        current_memory = await self.config.memory()
        current_memory.pop(guild_id, None)
        await self.config.memory.set(current_memory)
        await ctx.send("Server-wide memory cleared.")

    @commands.command()
    async def memoryusage(self, ctx):
        """Check memory usage for the current server."""
        guild_id = str(ctx.guild.id if ctx.guild else ctx.channel.id)
        memory = self.memory.get(guild_id, [])
        size_bytes = len(json.dumps(memory).encode("utf-8"))
        size_mb = size_bytes / (1024 * 1024)
        await ctx.send(f"Current memory usage: {size_mb:.2f} MB / {MAX_MEMORY_BYTES / (1024 * 1024):.2f} MB")

    @commands.command()
    async def generateimage(self, ctx, *, description: str):
        """Generate an image from a description using DALL-E."""
        api_key = await self.config.api_key()
        if not api_key:
            await ctx.send("OpenAI API key is not set. Please set it using `!setapikey`.")
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
        model = await self.config.model()
        if not api_key:
            await message.channel.send("OpenAI API key is not set. Please set it using `!setapikey`.")
            return

        try:
            async with message.channel.typing():
                client = AsyncOpenAI(api_key=api_key)
                guild_id = str(message.guild.id if message.guild else message.channel.id)

                # Load from memory config if not in local cache
                if guild_id not in self.memory:
                    current_memory = await self.config.memory()
                    self.memory[guild_id] = current_memory.get(guild_id, [])

                history = self.memory[guild_id]
                all_members = {m.id: f"{m.display_name} ({m.name}#{m.discriminator})" for m in message.guild.members} if message.guild else {}
                sender_info = all_members.get(message.author.id, f"{message.author.display_name} ({message.author.name}#{message.author.discriminator})")
                formatted_input = f"{sender_info}: {query}"
                history.append({"role": "user", "content": formatted_input})

                response = await client.chat.completions.create(
                    model=model,
                    messages=history[-10:],
                    max_tokens=1024
                )

                reply = response.choices[0].message.content.strip()
                history.append({"role": "assistant", "content": reply})

                # Enforce memory size limit
                json_size = len(json.dumps(history).encode("utf-8"))
                while json_size > MAX_MEMORY_BYTES:
                    if history:
                        history.pop(0)
                        json_size = len(json.dumps(history).encode("utf-8"))
                    else:
                        break

                self.memory[guild_id] = history

                # Save to persistent config
                current_memory = await self.config.memory()
                current_memory[guild_id] = history
                await self.config.memory.set(current_memory)

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
