import json
import base64
import discord
import aiohttp
from io import BytesIO
from collections import defaultdict

from redbot.core import commands, Config
from redbot.core.bot import Red

from openai import AsyncOpenAI


# -----------------------------
# CONFIG
# -----------------------------
MAX_MEMORY_BYTES = 10 * 1024 * 1024  # 10MB memory cap

DEFAULT_MODEL = "gpt-4o"
DEFAULT_IMAGE_MODEL = "gpt-image-1"


# -----------------------------
# COG
# -----------------------------
class AskChatGPT(commands.Cog):

    def __init__(self, bot: Red):
        self.bot = bot

        self.config = Config.get_conf(
            self,
            identifier=1234567890,
            force_registration=True,
        )

        self.config.register_global(
            api_key=None,
            model=DEFAULT_MODEL,
            image_model=DEFAULT_IMAGE_MODEL,
            memory={}
        )

        self.memory = defaultdict(list)

    # -----------------------------
    # Helpers
    # -----------------------------
    async def _get_client(self):
        api_key = await self.config.api_key()
        if not api_key:
            return None
        return AsyncOpenAI(api_key=api_key)

    def _scope_id(self, obj):
        guild = getattr(obj, "guild", None)
        channel = getattr(obj, "channel", None)

        if guild:
            return str(guild.id)
        if channel:
            return str(channel.id)

        return "unknown"

    async def _load_history(self, scope_id):
        if scope_id in self.memory:
            return self.memory[scope_id]

        stored = await self.config.memory()
        self.memory[scope_id] = stored.get(scope_id, [])
        return self.memory[scope_id]

    async def _save_history(self, scope_id, history):
        size = len(json.dumps(history).encode("utf-8"))

        while size > MAX_MEMORY_BYTES and history:
            history.pop(0)
            size = len(json.dumps(history).encode("utf-8"))

        self.memory[scope_id] = history

        stored = await self.config.memory()
        stored[scope_id] = history
        await self.config.memory.set(stored)

    async def send_long_message(self, channel, content):
        if not content:
            content = "(empty response)"

        for i in range(0, len(content), 2000):
            await channel.send(content[i:i + 2000])

    def _format_user_line(self, message, query):
        if message.guild:
            sender = f"{message.author.display_name} ({message.author})"
        else:
            sender = message.author.display_name
        return f"{sender}: {query}"

    # ---------- IMPORTANT ----------
    # Build plain transcript input
    # (works across OpenAI + proxies)
    def _build_transcript(self, history_slice):
        lines = []
        for msg in history_slice:
            role = msg.get("role")
            text = msg.get("content", "")

            if role == "assistant":
                lines.append(f"Assistant: {text}")
            else:
                lines.append(f"User: {text}")

        return "\n".join(lines)

    async def _friendly_error(self, e):
        s = str(e)
        model = await self.config.model()

        if "model_not_found" in s:
            return (
                f"Model `{model}` not accessible.\n"
                "Try: `!setmodel gpt-4o`"
            )

        return f"An error occurred: {s}"

    # -----------------------------
    # Commands
    # -----------------------------
    @commands.command()
    async def setapikey(self, ctx, *, key: str):
        await self.config.api_key.set(key.strip())
        await ctx.send("API key updated.")

    @commands.command()
    async def setmodel(self, ctx, *, model: str):
        model = model.lower().strip()
        await self.config.model.set(model)
        await ctx.send(f"Model updated to `{model}`.")

    @commands.command()
    async def setimagemodel(self, ctx, *, model: str):
        model = model.lower().strip()
        await self.config.image_model.set(model)
        await ctx.send(f"Image model updated to `{model}`.")

    @commands.command()
    async def modelstatus(self, ctx):
        t = await self.config.model()
        i = await self.config.image_model()
        await ctx.send(f"Text model: `{t}`\nImage model: `{i}`")

    @commands.command()
    async def clearmemory(self, ctx):
        sid = self._scope_id(ctx)
        self.memory.pop(sid, None)

        stored = await self.config.memory()
        stored.pop(sid, None)
        await self.config.memory.set(stored)

        await ctx.send("Memory cleared.")

    @commands.command()
    async def memoryusage(self, ctx):
        sid = self._scope_id(ctx)
        history = await self._load_history(sid)

        size = len(json.dumps(history).encode("utf-8"))
        await ctx.send(f"Memory usage: {size/1024/1024:.2f} MB")

    # -----------------------------
    # Image Generation
    # -----------------------------
    @commands.command()
    async def generateimage(self, ctx, *, description: str):

        client = await self._get_client()
        if not client:
            await ctx.send("Set API key first with `!setapikey`.")
            return

        model = await self.config.image_model()

        try:
            async with ctx.typing():

                resp = await client.images.generate(
                    model=model,
                    prompt=description,
                    size="1024x1024",
                    n=1,
                )

                item = resp.data[0]

                image_data = None

                # URL response
                image_url = getattr(item, "url", None)
                if isinstance(image_url, str):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url) as r:
                            image_data = await r.read()

                # Base64 fallback
                if image_data is None:
                    b64 = getattr(item, "b64_json", None)
                    if isinstance(b64, str):
                        image_data = base64.b64decode(b64)

                if image_data is None:
                    await ctx.send(
                        f"No image returned. Try `!setimagemodel gpt-image-1`."
                    )
                    return

                fp = BytesIO(image_data)
                fp.seek(0)

                await ctx.send(file=discord.File(fp, "generated.png"))

        except Exception as e:
            await ctx.send(await self._friendly_error(e))

    # -----------------------------
    # Mention Listener
    # -----------------------------
    @commands.Cog.listener("on_message")
    async def on_mention(self, message: discord.Message):

        if message.author.bot:
            return
        if not self.bot.user:
            return
        if self.bot.user not in message.mentions:
            return

        content = message.content.replace(f"<@!{self.bot.user.id}>", "")
        content = content.replace(f"<@{self.bot.user.id}>", "")
        content = content.strip()

        if not content:
            await message.channel.send("Say something after mentioning me 🙂")
            return

        await self.handle_askgpt(message, content)

    # -----------------------------
    # Chat Handler
    # -----------------------------
    async def handle_askgpt(self, message, query):

        client = await self._get_client()
        if not client:
            await message.channel.send("Set API key first.")
            return

        model = await self.config.model()

        sid = self._scope_id(message)
        history = await self._load_history(sid)

        formatted = self._format_user_line(message, query)
        history.append({"role": "user", "content": formatted})

        try:
            async with message.channel.typing():

                transcript = self._build_transcript(history[-10:])

                resp = await client.responses.create(
                    model=model,
                    input=transcript,
                    max_output_tokens=1024,
                )

                reply = (getattr(resp, "output_text", "") or "").strip()
                if not reply:
                    reply = "(No response text returned.)"

                history.append({"role": "assistant", "content": reply})

                await self._save_history(sid, history)
                await self.send_long_message(message.channel, reply)

        except Exception as e:
            await message.channel.send(await self._friendly_error(e))


async def setup(bot: Red):
    await bot.add_cog(AskChatGPT(bot))
