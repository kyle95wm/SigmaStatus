import discord
from discord.ext import commands

from bot.config import load_config
from bot.db import ReportDB

DEFAULT_GUILD_ID_FOR_SYNC = 1457559352717086917


class SigmaReportsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        self.cfg = load_config()
        self.db = ReportDB(self.cfg.db_path)

    async def setup_hook(self) -> None:
        for ext in ("bot.cogs.plex_liveboard",):
            try:
                await self.load_extension(ext)
            except Exception as e:
                print(f"⚠️  Skipping {ext}: {repr(e)}")

        # Sync to a single guild for fast iteration
        guild_id = getattr(self.cfg, "guild_id", None) or DEFAULT_GUILD_ID_FOR_SYNC
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"Synced {len(synced)} commands to guild {guild_id}")
            except Exception as e:
                print(f"⚠️  Command sync failed: {repr(e)}")
        else:
            print("⚠️  No guild_id configured; skipping guild sync.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")


def main():
    bot = SigmaReportsBot()
    bot.run(bot.cfg.token)


if __name__ == "__main__":
    main()
