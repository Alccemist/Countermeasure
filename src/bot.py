"""
INFORMATION

		This contains the bot's functionality. The guild ID and bot token do not belong here.
	Guild ID and bot token are used in .tree.command(...) and client.run(...), for command development and bot identification respectively.
	Actual event handling is addressed in event_handler.py 
	Everything is arranged and initialized in main.py
	This bot exclusively uses slash commands. Sensitive config information should be stored in config/.env

"""
import database, discord, os
from discord.ext import commands
from utility_libs.scheduler import PayoutScheduler

class CountermeasureClient(commands.Bot):
	def __init__(self, *, admin_role:int, command_prefix:str, intents:discord.Intents, debug_guild:int):
		super().__init__(command_prefix=command_prefix, intents=intents) # To let instances build themselves
		self.admin_role_id:int = admin_role
		self.cmd_prefix:str = command_prefix
		self.db = None
		self.debug_guild:int = debug_guild

	async def setup_hook(self):
		# 0. Setup: Get channel ID(s)
		self.announce_channel = int(os.getenv("ANNOUNCE_CHANNEL_ID"))

		# 1. Open one persistent connection
		print("Setting up database...")
		await database.initialize_database()
		self.db = await database.connect_database()

		# 2. Load cogs ==> scheduler_cog will read self.db / self.announce_channel
		print("Loading cogs/extensions...")
		for filename in os.listdir("src\\cogs"):
			if filename.endswith(".py") and filename != "__init__.py":
				cog = f"cogs.{filename[:-3]}" # Because load_extension expects the name without .py
				try:
					await self.load_extension(cog)
				except Exception as e:
					print(f"Failed to load extension: {e}")

		# 3. Set up scheduler
		#	==> We expect the scheduler_cog to run everything, including check_status
		
		# Extra Dev sync
		# ==> Show what’s in the tree *before* sync. Debug use
		# ==> print("Tree commands before sync:", [c.qualified_name for c in self.tree.get_commands()])

		# Debug-Guild-Only sync for quick iteration
		if self.debug_guild:
			g = discord.Object(id=self.debug_guild)
			print(f"Attempting to sync with guild {self.debug_guild}...")
			self.tree.copy_global_to(guild=g)
			cmds = await self.tree.sync(guild=g)
			print(f"Synced {len(cmds)} commands to guild {self.debug_guild}: {[c.name for c in cmds]}")
		else:
			cmds = await self.tree.sync()
			print(f"Synced {len(cmds)} commands to global: {[c.name for c in cmds]}")

	async def on_ready(self):
		print(f"CLIENT READY: {self.user} <{self.user.id}>")

	async def close(self):
		if self.db:
			await database.close(self.db)
		await super().close()

