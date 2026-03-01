import json
import discord
import aiohttp
from io import BytesIO
from collections import defaultdict

from redbot.core import commands, Config
from redbot.core.bot import Red

from openai import AsyncOpenAI

# Memory limit in BYTES (10 MB here; increase if you want)
MAX_MEMORY_BYTES = 10 * 1024 * 1024

DEFAULT_MODEL = "gpt-4o"          # safe default
DEFAULT_IMAGE_MODEL = "gpt-image-1"


class AskChatGPT(commands.Cog):
    """A Redbot cog to interact with OpenAI (Responses API + Images) with server-wide memory."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_global(
            api_key=None,
            model=DEFAULT_MODEL,
            image_model=DEFAULT_IMAGE_MODEL,
            memory={}
        )

        # In-memory cache per guild/channel
        self.memory = defaultdict(list)  # {scope_id: [messages...]}

    # -----------------------------
    # Helpers
    # -----------------------------
    async def _get_client(self):
        api_key = await self.config.api_key()
        if not api_key:
            return None
        return AsyncOpenAI(api_key=api_key)

    def _scope_id(self, message_or_ctx):
        """Scope memory to guild if available; otherwise to channel id (DMs)."""
        guild = getattr(message_or_ctx, "guild", None)
        channel = getattr(message_or_ctx, "channel", None)
        if guild:
            return str(guild.id)
        if channel:
            return str(channel.id)
        return "unknown"

    async def _load_history(self, scope_id):
        if scope_id in self.memory:
            return self.memory[scope_id]
        current_memory = await self.config.memory()
        self.memory[scope_id] = current_memory.get(scope_id, [])
        return self.memory[scope_id]

    async def _save_history(self, scope_id, history):
        # Enforce memory size limit
        json_size = len(json.dumps(history).encode("utf-8"))
        while json_size > MAX_MEMORY_BYTES and history:
            history.pop(0)
            json_size = len(json.dumps(history).encode("utf-8"))

        self.memory[scope_id] = history

        current_memory = await self.config.memory()
        current_memory[scope_id] = history
        await self.config.memory.set(current_memory)

    async def send_long_message(self, channel, content):
        max_length = 2000
        if not content:
            content = "(empty response)"
        for i in range(0, len(content), max_length):
            await channel.send(content[i:i + max_length])

    def _format_user_line(self, message, query):
        if message.guild:
            sender = f"{message.author.display_name} ({message.author.name}#{message.author.discriminator})"
        else:
            sender = f"{message.author.display_name}"
        return f"{sender}: {query}"

    def _build_transcript_input(self, history_slice):
        """
        Build a plain-text transcript for endpoints that don't accept structured input blocks.
        history_slice items are like: {"role": "user"/"assistant", "content": "..."}
        """
        lines = []
        for msg in history_slice:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "assistant":
                lines.append(f"Assistant: {text}")
            else:
                lines.append(f"User: {text}")
        return "\n".join(lines)

    async def _friendly_error(self, e):
        s = str(e)
        model = await self.config.model()

        if "model_not_found" in s or "does not exist or you do not have access" in s:
            return (
                f"OpenAI rejected the model `{model}`.\n"
                f"- Use lowercase model ids (example: `gpt-5.2`, not `GPT-5.2`).\n"
                f"- Confirm your API key has access to that model.\n"
                f"\nTry `!setmodel gpt-4o` to verify the bot works, then switch back."
            )

        return f"An error occurred: {s}"

    # -----------------------------
    # Commands
    # -----------------------------
    @commands.command()
    async def setapikey(self, ctx, *, key: str):
        """Set the OpenAI API key."""
        await self.config.api_key.set(key.strip())
        await ctx.send("API key updated successfully.")

    @commands.command()
    async def setmodel(self, ctx, *, model: str):
        """Set the OpenAI text model. Example: !setmodel gpt-5.2"""
        model = model.strip().lower()
        await self.config.model.set(model)
        await ctx.send(f"Model updated to `{model}`.")

    @commands.command()
    async def setimagemodel(self, ctx, *, model: str):
        """Set the OpenAI image model. Default is gpt-image-1."""
        model = model.strip().lower()
        await self.config.image_model.set(model)
        await ctx.send(f"Image model updated to `{model}`.")

    @commands.command()
    async def modelstatus(self, ctx):
        """Show current configured text and image models."""
        text_model = await self.config.model()
        image_model = await self.config.image_model()
        await ctx.send(f"Text model: `{text_model}`\nImage model: `{image_model}`")

    @commands.command()
    async def clearmemory(self, ctx):
        """Clear memory for this server/channel."""
        scope_id = self._scope_id(ctx)
        self.memory.pop(scope_id, None)

        current_memory = await self.config.memory()
        current_memory.pop(scope_id, None)
        await self.config.memory.set(current_memory)

        await ctx.send("Memory cleared for this server/channel.")

    @commands.command()
    async def memoryusage(self, ctx):
        """Check memory usage for the current server/channel."""
        scope_id = self._scope_id(ctx)
        history = await self._load_history(scope_id)
        size_bytes = len(json.dumps(history).encode("utf-8"))
        size_mb = size_bytes / (1024 * 1024)
        limit_mb = MAX_MEMORY_BYTES / (1024 * 1024)
        await ctx.send(f"Current memory usage: {size_mb:.2f} MB / {limit_mb:.2f} MB")

    @commands.command()
    async def models(self, ctx):
        """List available models for your API key (best-effort)."""
        client = await self._get_client()
        if not client:
            await ctx.send("OpenAI API key is not set. Use `!setapikey`.")
            return

        try:
            resp = await client.models.list()
            ids = []
            for m in getattr(resp, "data", [])[:30]:
                mid = getattr(m, "id", None)
                if mid:
                    ids.append(mid)
            if not ids:
                await ctx.send("No models returned by this endpoint/key.")
                return
            await self.send_long_message(ctx.channel, "Models (first 30):\n" + "\n".join(f"- `{i}`" for i in ids))
        except Exception as e:
            await ctx.send(f"Could not list models: {str(e)}")

    @commands.command()
    async def generateimage(self, ctx, *, description: str):
        """Generate an image from a description."""
        client = await self._get_client()
        if not client:
            await ctx.send("OpenAI API key is not set. Please set it using `!setapikey`.")
            return

        image_model = await self.config.image_model()

        try:
            async with ctx.typing():
                resp = await client.images.generate(
                    model=image_model,
                    prompt=description,
                    n=1,
                    size="1024x1024",
                )

                image_url = resp.data[0].url
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as r:
                        if r.status != 200:
                            await ctx.send(f"Failed to download image (HTTP {r.status}).")
                            return
                        image_data = await r.read()

                image = BytesIO(image_data)
                image.seek(0)
                await ctx.send(file=discord.File(image, "generated_image.png"))

        except Exception as e:
            await ctx.send(await self._friendly_error(e))

    # -----------------------------
    # Mention handler (chat)
    # -----------------------------
    @commands.Cog.listener("on_message")
    async def on_mention(self, message: discord.Message):
        if message.author.bot:
            return
        if not self.bot.user:
            return
        if self.bot.user not in message.mentions:
            return

        content = message.content.replace(f"<@!{self.bot.user.id}>", "").strip()
        content = content.replace(f"<@{self.bot.user.id}>", "").strip()

        if not content:
            await message.channel.send("Say something after mentioning me 🙂")
            return

        await self.handle_askgpt(message, content)

    async def handle_askgpt(self, message: discord.Message, query: str):
        client = await self._get_client()
        if not client:
            await message.channel.send("OpenAI API key is not set. Please set it using `!setapikey`.")
            return

        model = (await self.config.model()).strip().lower()
        scope_id = self._scope_id(message)
        history = await self._load_history(scope_id)

        formatted_input = self._format_user_line(message, query)
        history.append({"role": "user", "content": formatted_input})

        try:
            async with message.channel.typing():
                # IMPORTANT: send a plain string transcript (no structured content blocks)
                transcript = self._build_transcript_input(history[-10:])

                resp = await client.responses.create(
                    model=model,
                    input=transcript,
                    max_output_tokens=1024,
                )

                reply = (getattr(resp, "output_text", "") or "").strip()
                if not reply:
                    reply = "(No text returned by the model.)"

                history.append({"role": "assistant", "content": reply})
                await self._save_history(scope_id, history)

                await self.send_long_message(message.channel, reply)

        except Exception as e:
            # Roll back last user message so failed calls don't pollute memory
            try:
                if history and history[-1].get("role") == "user" and history[-1].get("content") == formatted_input:
                    history.pop()
                    await self._save_history(scope_id, history)
            except Exception:
                pass

            await message.channel.send(await self._friendly_error(e))


async def setup(bot: Red):
    await bot.add_cog(AskChatGPT(bot))
