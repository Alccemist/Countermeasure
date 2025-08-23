"""
INFORMATION

		Main.py is where everything is set into motion.
"""

""" [IMPORTS] """
import discord, logging, os, sys
from utility_libs import utilities

""" [SETUP] """
setup_util = utilities.SetupUtilities()
setup_status = setup_util.HandleSetup()
logger = logging.FileHandler(filename="Countermeasure_Main.log", encoding='utf-8', mode='w')
CMD_PREFIX = "<<"  # PREFIX DEPRECATED... Has no use.

if setup_status:
	ADMIN_ROLE = int(os.getenv("ADMIN_ROLE_ID"))
	DEBUG_GUILD = int(os.getenv("DEBUG_GUILD_ID"))
	TOKEN = str(os.getenv("TOKEN"))
	from bot import CountermeasureClient
else:
	print("Error with setup. Please delete any files in src/config and restart from main.py.")
	sys.exit()

# <Initialize Discord, instantiate client (bot)>
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True 
intents.members = True

client = CountermeasureClient(
	admin_role=ADMIN_ROLE,
	command_prefix=CMD_PREFIX,
	intents=intents,
	debug_guild=DEBUG_GUILD
)

client.run(TOKEN, log_handler=logger, log_level = logging.DEBUG)