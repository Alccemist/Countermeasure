"""
INFORMATION

	Main.py is where everything is set into motion.
	Please create & fill out .env before running the bot.

"""

""" [IMPORTS] """
import discord, logging, os
from bot import CountermeasureClient
from discord.ext.commands import Bot
from dotenv import load_dotenv
# Not yet complete... we will fill out bot.py and import our bot. Keeps main.py elegant. 

""" [SETUP] """
load_dotenv(dotenv_path="src\\config\\.env")
logger = logging.FileHandler(filename="Countermeasure_Main.log", encoding='utf-8', mode='w')

""" [CONFIG] """
# ==> REMOVE THESE BEFORE PUSHING!!!
# ==> See documentation for config details.
ADMIN_ROLE_ID:int = int(os.getenv("ADMIN_ROLE_ID"))
TOKEN:str = str(os.getenv("TOKEN"))
DEBUG_GUILD_ID:int = int(os.getenv("DEBUG_GUILD_ID"))
CMD_PREFIX = "<<"  # PREFIX DEPRECATED... Has no use.


# <Initialize Discord, Bot>
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True 
intents.members = True

client = CountermeasureClient(
	admin_role=ADMIN_ROLE_ID,
	command_prefix=CMD_PREFIX,
	intents=intents,
	debug_guild=DEBUG_GUILD_ID
)

client.run(TOKEN, log_handler=logger, log_level = logging.DEBUG)