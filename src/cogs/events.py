"""
INFORMATION

	This is our events library. It addresses the automatic events in our server.
	
"""
import discord
from discord.ext import commands

class Events(commands.Cog):
	def __init__(self, bot:commands.Bot) -> None:
		self.bot = bot

	# Listeners (classic events)
	@commands.Cog.listener()
	async def on_member_join(self, member:discord.Member):		
		print(f"[LOG]: From {self}: {member.name} has joined the server...")
		# [Welcome Member]
		try:
			await member.send(f"Welcome to {member.guild.name}. Please read the rules.")
		except discord.Forbidden:
			pass
		# await self.bot.db_add_user(member) ==> Moved to scheduler... probably using db_add_user

	@commands.Cog.listener()
	async def on_member_leave(self, member:discord.Member):
		print(f"[LOG]: From {self}: {member.name} left... Removing from DB")
		await self.bot.db_remove_user(member)

async def setup(bot:commands.Bot):
	await bot.add_cog(Events(bot))
	print("[cogs.events] added... current tree: ", [c.qualified_name for c in bot.tree.get_commands()])