from redbot.core import commands, Config

class WordTracker(commands.Cog):
    """A cog to track the usage of a specific word in chat messages and record user-specific counts."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_global = {
            "word_count": 0,
            "tracked_word": "happiness",
            "user_counts": {}  # Stores counts per user
        }
        self.config.register_global(**default_global)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:  # Skip bot messages
            return

        tracked_word = await self.config.tracked_word()
        if tracked_word is None:
            return

        if tracked_word in message.content.lower():
            # Increment the global count
            current_count = await self.config.word_count()
            if current_count is None:
                current_count = 0
            await self.config.word_count.set(current_count + 1)

            # Increment the user-specific count
            user_counts = await self.config.user_counts()
            if user_counts is None:
                user_counts = {}
            user_id = str(message.author.id)  # Convert to string for JSON storage
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
            await self.config.user_counts.set(user_counts)

    @commands.command()
    async def wordcount(self, ctx):
        """Shows how many times the tracked word has been mentioned by each user, ranked."""
        word = await self.config.tracked_word()
        if word is None:
            await ctx.send("Tracked word is not set.")
            return

        user_counts = await self.config.user_counts()
        if not user_counts:
            await ctx.send(f"No mentions of '{word}' have been recorded.")
            return

        # Create a sorted list of tuples (user_id, count) in descending order of count
        sorted_counts = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
        message_lines = [f"User <@{user_id}> mentioned '{word}' {count} times." for user_id, count in sorted_counts]

        await ctx.send("\n".join(message_lines))

    @commands.command()
    @commands.is_owner()  # This makes the command only usable by the bot owner
    async def settrackedword(self, ctx, *, new_word: str):
        """Sets a new word to track."""
        await self.config.tracked_word.set(new_word.lower())
        await self.config.user_counts.set({})  # Reset user counts when changing the word
        await ctx.send(f"The new tracked word is '{new_word}'.")

async def setup(bot):
    cog = WordTracker(bot)
    await bot.add_cog(cog)
