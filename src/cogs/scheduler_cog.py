"""
INFORMATION

	This is our scheduler cog. The bot interacts with our scheduler through here.
	
"""
import aiosqlite, utility_libs.scheduler as scheduler
from discord.ext import commands
from datetime import datetime, timezone

class SchedulerCog(commands.Cog):
	def __init__(self, bot:commands.Bot, db:aiosqlite.Connection, announce_channel:int) -> None:
		self.bot = bot
		self.db = db
		self.announce_channel = announce_channel

		async def announce(msg:str):
			channel = await self.bot.fetch_channel(self.announce_channel)
			await channel.send(msg)

		self.PaySch = scheduler.PayoutScheduler(db, announce)

	async def cog_load(self):
		self.PaySch.is_ready()
		await self.PaySch.start()

async def setup(bot:commands.Bot):
	await bot.add_cog(SchedulerCog(bot, bot.db, bot.announce_channel))
	print("[cogs.scheduler_cog] added... current tree: ", [c.qualified_name for c in bot.tree.get_commands()])