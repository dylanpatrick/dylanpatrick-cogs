import aiohttp
import discord
import json
from redbot.core import commands

def load_api_key():
    with open("config.json", "r") as f:
        config = json.load(f)
    return config["chatgpt_api_key"]

class ChatGPT(commands.Cog):
    """ChatGPT integration for Redbot."""

    def __init__(self, bot):
        self.bot = bot
        self.api_key = load_api_key()

    @commands.command()
    async def askgpt(self, ctx, *, question: str):
        """Ask a question to ChatGPT."""

        url = "https://api.openai.com/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        prompt = f"{question}\nAnswer:"
        data = {
            "model": "gpt-3.5-turbo",
            "prompt": prompt,
            "max_tokens": 50,
            "n": 1,
            "stop": None,
            "temperature": 0.8
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    json_response = await response.json()
                    answer = json_response["choices"][0]["text"].strip()
                    await ctx.send(answer)
                else:
                    await ctx.send("Error: Unable to get a response from ChatGPT.")

    @commands.command()
    @commands.is_owner()
    async def updategptkey(self, ctx, *, new_key: str):
        """Update the ChatGPT API key. Only the bot owner can use this command."""

        # Update the API key in the config file
        with open("config.json", "r") as f:
            config = json.load(f)

        config["chatgpt_api_key"] = new_key

        with open("config.json", "w") as f:
            json.dump(config, f)

        # Update the API key in the class instance
        self.api_key = new_key
        await ctx.send("ChatGPT API key has been successfully updated.")
