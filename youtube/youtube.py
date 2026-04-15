import asyncio
from typing import List

from redbot.core import commands
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

try:
    from yt_dlp import YoutubeDL
except ImportError:
    YoutubeDL = None


class YouTube(commands.Cog):
    """Search YouTube for videos."""

    def __init__(self, bot):
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    async def _youtube_results(self, query: str, limit: int = 10) -> List[str]:
        """
        Search YouTube using yt-dlp and return a list of watch URLs.
        """
        if YoutubeDL is None:
            return [
                "yt-dlp is not installed. Install it in the same environment as Redbot with: "
                "`pip install -U yt-dlp`"
            ]

        loop = asyncio.get_running_loop()

        def do_search() -> List[str]:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": True,
                "default_search": "ytsearch",
            }

            results: List[str] = []
            seen = set()

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

            entries = info.get("entries", []) if isinstance(info, dict) else []

            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                video_id = entry.get("id")
                webpage_url = entry.get("url") or entry.get("webpage_url")
                ie_key = entry.get("ie_key")

                # Prefer actual YouTube video results
                if video_id and ie_key in {"Youtube", "YoutubeTab"}:
                    url = f"https://www.youtube.com/watch?v={video_id}"
                elif video_id and not webpage_url:
                    url = f"https://www.youtube.com/watch?v={video_id}"
                elif isinstance(webpage_url, str) and "youtube.com/watch" in webpage_url:
                    url = webpage_url
                elif isinstance(webpage_url, str) and "youtu.be/" in webpage_url:
                    url = webpage_url
                else:
                    continue

                if url not in seen:
                    seen.add(url)
                    results.append(url)

            return results

        try:
            return await loop.run_in_executor(None, do_search)
        except Exception as e:
            return [f"Something went terribly wrong! [{type(e).__name__}: {e}]"]

    @commands.command()
    async def youtube(self, ctx, *, query: str):
        """Search YouTube and return the top result."""
        result = await self._youtube_results(query, limit=5)

        if result:
            await ctx.send(result[0])
        else:
            await ctx.send("Nothing found. Try again later.")

    @commands.command()
    async def ytsearch(self, ctx, *, query: str):
        """Search YouTube and show multiple results."""
        result = await self._youtube_results(query, limit=10)

        if result:
            await menu(ctx, result, DEFAULT_CONTROLS)
        else:
            await ctx.send("Nothing found. Try again later.")
