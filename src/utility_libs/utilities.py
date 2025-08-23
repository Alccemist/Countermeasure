"""
INFORMATION

	Utilities contains some helper functions, like checking if a player is an admin.
	Many functions are designed around interactions. None accomodate prefix commands.

"""
import discord, sys, typing
from collections import deque
from datetime import datetime, date
from discord.ext import commands
from typing import List
from pathlib import Path
from dotenv import load_dotenv

""" [SETUP] """
SRC_DIR = Path(__file__).resolve().parents[1]
print(SRC_DIR)
ENV_PATH = SRC_DIR/".env"

class SetupUtilities:
	"""
	SetupUtilities is used for creating our .env file. For new users or restarts.
	"""
	def HandleSetup(self) -> bool:
		# ==> Returns True if we're ready and our .env has been loaded.
		if not ENV_PATH.exists():
			print("No .env file found in src/env. Let's set one up.\n" \
			"Please have Discord developer mode enabled and a bot with 'server members' & 'message content' intents ready.\n" \
			"For more information, please read the README.")
			with open(ENV_PATH, "w") as f:
				f.write(f"ADMIN_ROLE_ID = {input('Server admin role ID [int]: ')}\n")
				f.write(f"ANNOUNCE_CHANNEL_ID = {input('Game or bot announcement channel ID [int]: ')}\n")
				f.write(f"DEBUG_GUILD_ID = {input('Server ID [int]: ')}\n")
				f.write(f"OBJECTS_PER_PAGE = {input('How many items in one catalogue page (10 suggested) [int]: ')}\n")
				f.write(f"PAYOUT_STEP = {input('Days between each payout [int]: ')}\n")
				f.write(f"SCHEDULER_RUNS_UTC = {input('Payouts should occur at this hour UTC [int]: ')}\n")
				f.write(f"TOKEN = {input('Bot token [str]: ')}\n")
			print(f"Created {ENV_PATH.absolute()}... Restart from main.py!")
			sys.exit()
		else:
			load_dotenv(ENV_PATH)
			return True
			
		


class LoggingUtilities:
	"""
	LoggingUtilities is used for recording information for debugging / testing / record-keeping purposes.
	Both logging and debug functionalities can be toggled.
	"""
	def __init__(self, log_enabled:bool, debug_enabled:bool) -> None:
		self.log_enabled = log_enabled
		self.debug_enabled = debug_enabled
		
	def print_log(self, s:str):
		if self.log_enabled: print(f"[LOG]: {s}")
	
	def print_debug(self, s:str):
		if self.debug_enabled: print(f"[DEBUG]: {s}")

class RoleUtilities:
	def __init__(self, admin_role_id:typing.Optional[int]):
		self.admin_role_id = admin_role_id

		self.error_color = discord.Color.red()

	# [check_utils_status] prints out information on the instance's existence.
	async def check_utils_status(self, client:commands.Bot, admin_role_id:int) -> None:
		print(f"[LOG]: At {self},\n		fetched client <{client}> and admin ID <{admin_role_id}>... Library is callable...")
		return

	# [is_admin] is mostly used in user commands.
	# ==> We expect a guild Member, not simply a user, so we can access roles.
	def has_admin(self, user_roles:list[int], admin_role_id:int) -> bool:
		return any(r.id == admin_role_id for r in user_roles)
	
	# [is_role] is primarily for debug. May have some application.
	def has_role(self, user_roles:list[int], role_id:int) -> bool:
		return any(r.id == role_id for r in user_roles)


	""" ~~[err_not_... FAMILY]~~ """
	# These are error message senders that can be called when a member is lacking a required quality.

	async def err_not_role(self, itx:discord.Interaction, role:discord.Role):
		e = discord.Embed(color=self.error_color)
		e.description = f"ERROR: Missing role {role}..."
		await itx.channel.send(embed=e)
		return

	async def err_not_admin(self, itx:discord.Interaction):
		e = discord.Embed(color=self.error_color)
		e.description = "ERROR: Not an admin..."
		await itx.channel.send(embed=e)
		return

class SchedulerUtilities:
	def __init__(self) -> None:
		pass
	# Parse a string date -> date
	def parse_date(self,s:str) -> date:
		return datetime.strptime(s, "%Y-%m-%d").date()
	
class RenderUtilities:
	class Paginator(discord.ui.View):
		def __init__(
				self, 
				*, 
				embeds:List[discord.Embed],
				timeout:float|None = 30
			) -> None:
				super().__init__(timeout=timeout)

				self._embeds = embeds
				self._queue = deque(embeds)
				self._initial = embeds[0]
				self._len = len(embeds)
				self._current_page = 1

		""" [BUTTONS] """
		# ==> Buttons handle queue traversal and response editing.

		@discord.ui.button(label="<-")
		async def previous(self, itx:discord.Interaction, _):
			self._queue.rotate(1) # ==> Rotate is CCW, i.e. traverse back by 1
			embed = self._queue[0] # ==> [0] was previously 1
			await itx.response.edit_message(embed=embed)

		@discord.ui.button(label="->")
		async def next(self, itx:discord.Interaction, _):
			self._queue.rotate(-1)
			embed = self._queue[0] # ==> [0] was previously "[-1]"
			await itx.response.edit_message(embed=embed)

		""" [initial PROPERTY] """
		# ==> A "getter" property that returns our initial embeds[0].
		@property
		def initial(self) -> discord.Embed:
			return self._initial