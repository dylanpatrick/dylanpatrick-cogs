from redbot.core import commands, Config
import re

class WordTracker(commands.Cog):
    """A cog to track usage counts for multiple words in chat messages."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_global = {
            "tracked_words": [],  # List of words being tracked
            "word_counts": {},    # Global counts per word
            "user_counts": {}     # Counts per word per user: {word: {user_id: count}}
        }
        self.config.register_global(**default_global)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        content = message.content.lower()
        tracked_words = await self.config.tracked_words()
        if not tracked_words:
            return
        # Prepare config values
        global_counts = await self.config.word_counts()
        user_counts = await self.config.user_counts()
        updated_global = False
        updated_users = False

        for word in tracked_words:
            # Use regex word boundaries for full words, escape special chars
            pattern = rf"\b{re.escape(word.lower())}\b"
            matches = re.findall(pattern, content)
            count = len(matches)
            if count > 0:
                # Update global count
                global_counts[word] = global_counts.get(word, 0) + count
                updated_global = True
                # Update per-user count
                w_users = user_counts.get(word, {})
                uid = str(message.author.id)
                w_users[uid] = w_users.get(uid, 0) + count
                user_counts[word] = w_users
                updated_users = True

        # Save if changed
        if updated_global:
            await self.config.word_counts.set(global_counts)
        if updated_users:
            await self.config.user_counts.set(user_counts)

    @commands.command()
    async def addword(self, ctx, *, word: str):
        """Adds a word to the tracked list."""
        word = word.lower()
        tracked = await self.config.tracked_words()
        if word in tracked:
            await ctx.send(f"'{word}' is already being tracked.")
            return
        tracked.append(word)
        await self.config.tracked_words.set(tracked)
        # Initialize counts
        global_counts = await self.config.word_counts()
        user_counts = await self.config.user_counts()
        global_counts.setdefault(word, 0)
        user_counts.setdefault(word, {})
        await self.config.word_counts.set(global_counts)
        await self.config.user_counts.set(user_counts)
        await ctx.send(f"Now tracking word: '{word}'")

    @commands.command()
    async def removeword(self, ctx, *, word: str):
        """Removes a word from tracking."""
        word = word.lower()
        tracked = await self.config.tracked_words()
        if word not in tracked:
            await ctx.send(f"'{word}' is not in the tracked list.")
            return
        tracked.remove(word)
        await self.config.tracked_words.set(tracked)
        # Remove counts
        global_counts = await self.config.word_counts()
        user_counts = await self.config.user_counts()
        global_counts.pop(word, None)
        user_counts.pop(word, None)
        await self.config.word_counts.set(global_counts)
        await self.config.user_counts.set(user_counts)
        await ctx.send(f"Stopped tracking word: '{word}'")

    @commands.command()
    async def listwords(self, ctx):
        """Lists all currently tracked words."""
        tracked = await self.config.tracked_words()
        if not tracked:
            await ctx.send("No words are currently being tracked.")
            return
        await ctx.send("Currently tracked words: " + ", ".join(f"'{w}'" for w in tracked))

    @commands.command()
    async def wordcount(self, ctx, *, word: str = None):
        """Displays counts for a specific word or all words if none specified."""
        tracked = await self.config.tracked_words()
        global_counts = await self.config.word_counts()
        user_counts = await self.config.user_counts()

        if word:
            word = word.lower()
            if word not in tracked:
                await ctx.send(f"'{word}' is not being tracked.")
                return
            total = global_counts.get(word, 0)
            users = user_counts.get(word, {})
            lines = [f"'{word}' total mentions: {total}"]
            if users:
                sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)
                lines += [f"User <@{uid}>: {cnt}" for uid, cnt in sorted_users]
            await ctx.send("\n".join(lines))
        else:
            if not tracked:
                await ctx.send("No words are currently being tracked.")
                return
            lines = []
            for w in tracked:
                total = global_counts.get(w, 0)
                lines.append(f"'{w}': {total} mentions")
            await ctx.send("\n".join(lines))

async def setup(bot):
    await bot.add_cog(WordTracker(bot))
