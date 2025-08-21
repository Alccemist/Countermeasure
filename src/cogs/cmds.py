	
"""
INFORMATION

		This contains all of our commands that users will execute. Table and data-related commands will often
	come with some kind of security check to avoid SQL injection.
	
"""

import database
import discord, os, typing
from discord import app_commands
from discord.ext import commands

""" [SETUP] """
DEBUG_GUILD_ID:int = int(os.getenv("DEBUG_GUILD_ID"))

# For our market embeds.
MARKET_COLORS = {
	"economy_market": discord.Color.gold(),
	"item_market": discord.Color.dark_grey(),
	"tech_market": discord.Color.blue(),
}

# ~~ [DEBUG FAMILY] ~~ 
# debug create embed is used to test embed features.
class Debug(commands.Cog):
	def __init__(self, bot:commands.Bot) -> None:
		self.bot = bot
	@app_commands.command(name="debug_create_embed",description="Test embed creation")
	@app_commands.guilds(discord.Object(id=DEBUG_GUILD_ID))
	async def debug_create_embed(self, interaction:discord.Interaction):
		embed = discord.Embed(
			title = "Debug",
			description = f"Hi, {interaction.user.name}",
			color = discord.Color.gold(),
			timestamp = interaction.created_at
			)
		embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
		embed.set_thumbnail(url=interaction.user.avatar.url)
		await interaction.response.send_message(embed=embed, ephemeral=False)

	# debug create input embed receives inputs for the embed that we're creating.
	@app_commands.command(name="debug_input_create_embed",description="Test embed w/ args creation")
	@app_commands.choices(clr=[
		app_commands.Choice(name="Default", value="default"),
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Orange", value="orange"),
		app_commands.Choice(name="Yellow", value="yellow"),
        app_commands.Choice(name="Green", value="green"),
        app_commands.Choice(name="Blue", value="blue"),
		app_commands.Choice(name="Purple", value="purple"),
        app_commands.Choice(name="Random", value="random"),
    ])
	@app_commands.guilds(discord.Object(id=DEBUG_GUILD_ID))
	async def debug_create_input_embed(
		self,
		interaction:discord.Interaction,
		title:typing.Optional[str] = None,
		desc:str = "",
		clr:typing.Optional[app_commands.Choice[str]] = None,
		has_timestamp:bool = False,
		thumbnail_url:typing.Optional[str] = None,
	):
		color_map = {
			"default":discord.Color.default(),
			"red":discord.Color.red(),
			"orange":discord.Color.orange(),
			"yellow":discord.Color.yellow(),
			"green":discord.Color.green(),
			"blue":discord.Color.blue(),
			"purple":discord.Color.purple(),
			"random":discord.Color.random()
		}

		embed = discord.Embed()
		embed.title = title
		embed.description = desc
		embed.color = color_map.get(clr.value if clr else "default", discord.Color.default())

		if has_timestamp:
			embed.timestamp = interaction.created_at
		embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
		embed.set_thumbnail(url=thumbnail_url)
		await interaction.response.send_message(embed=embed, ephemeral=False)

# ~~ [MARKET FAMILY] ~~
# Used to browse through and modify the market.
market = app_commands.Group(
	name="market",
	 description = "Browse available markets.",
	 guild_ids=[DEBUG_GUILD_ID]
)

@market.command(name="view_economies")
async def economies(itx:discord.Interaction):
	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetches the running client
	rows = await database.get_table(bot.db, "economy_market")
	print(bot.db)
	if not rows:
		return await itx.followup.send("No items found...", ephemeral = True)
	
	emb = discord.Embed(title="Economies", color=MARKET_COLORS["economy_market"])
	for row in rows: # we need to paginate this...
		name = row.get("economy_name")
		income = row.get("economy_income")
		cost = row.get("economy_cost")
		req_economy = row.get("req_economy")
		emb.add_field(name=name,value=f"Income: {income}\nCost: {cost}\nRequired Economy: {req_economy}", inline=False)

	await itx.followup.send(embed=emb)

@market.command(name="view_items")
async def items(itx:discord.Interaction):
	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client)
	rows = await database.get_table(bot.db, "item_market")
	if not rows:
		return await itx.followup.send("No items found...", ephemeral = True)
	
	emb = discord.Embed(title="Items", color=MARKET_COLORS["item_market"])
	for row in rows: # we need to paginate this...
		name = row.get("item_name")
		desc = row.get("description")
		cost = row.get("item_cost")
		stock = row.get("amt_in_stock")
		req_tech = row.get("req_tech")
		emb.add_field(name=name,value=f"{desc}\nCost: {cost}\nAmt. in stock: {stock}\nReq. Tech: {req_tech}", inline=False)

	await itx.followup.send(embed=emb)
	
@market.command(name="view_tech")
async def technology(itx:discord.Interaction):
	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client)
	rows = await database.get_table(bot.db, "tech_market")
	if not rows:
		return await itx.followup.send("No items found...", ephemeral = True)
	
	emb = discord.Embed(title="Technology", color=MARKET_COLORS["tech_market"])
	for row in rows: # we need to paginate this...
		name = row.get("tech_name")
		desc = row.get("description")
		cost = row.get("tech_cost")
		req_tech = row.get("req_tech")
		emb.add_field(name=name,value=f"{desc}\nCost: {cost}\nReq. Tech: {req_tech}", inline=False)

	await itx.followup.send(embed=emb)

@market.command(name="add_economy")
async def add_economy(
	itx:discord.Interaction,
	economy_name:str,
	economy_income:int,
	cost:int,
	req_economy:typing.Optional[str]
	):
	try:
		await itx.response.defer()
		bot = typing.cast(commands.Bot, itx.client)
		try:
			item = await database.add_economy(bot.db,economy_name=economy_name,economy_income=economy_income,cost=cost,req_economy=req_economy)
			if item:
				await itx.followup.send(f"Added status {economy_name} to the economy market.")
			else:
				await itx.followup.send(f"Economy status already exists!")
		except Exception as e:
			await itx.followup.send(f"[LOG]: <add_economy> ERROR CODE 0: {e}")
		
	except Exception as e:
		# Log server-side and notify the user cleanly
		msg = f"[LOG]: <add_economy> ERROR CODE 1: {type(e).__name__}: {e}"
		print(msg)
		await itx.followup.send(msg)
	
@market.command(name="add_item")
async def add_item(
	itx:discord.Interaction,
	item_name:str,
	desc:typing.Optional[str],
	cost:int,
	amt:int,
	max:int,
	req_tech:typing.Optional[str]
	):
	try:
		await itx.response.defer()
		bot = typing.cast(commands.Bot, itx.client)
		try:
			item = await database.add_item(db=bot.db,item_name=item_name,desc=desc,cost=cost,amt=amt,max=max,req_tech=req_tech)
			if item:
				await itx.followup.send(f"Added item {item_name} to the item market.")
			else:
				await itx.followup.send(f"Item already exists!")
		except Exception as e:
			await itx.followup.send(f"[LOG]: <add_item> ERROR CODE 0: {e}")
		
	except Exception as e:
		# Log server-side and notify the user cleanly
		msg = f"[LOG]: <add_item> ERROR CODE 1: {type(e).__name__}: {e}"
		print(msg)
		await itx.followup.send(msg)

@market.command(name="add_tech")
async def add_tech(
	itx:discord.Interaction,
	tech_name:str,
	desc:typing.Optional[str],
	tech_cost:int,
	req_tech:typing.Optional[str]
	):
	try:
		await itx.response.defer()
		bot = typing.cast(commands.Bot, itx.client)
		try:
			item = await database.add_tech(db=bot.db,tech_name=tech_name,desc=desc,tech_cost=tech_cost,req_tech=req_tech)
			if item:
				await itx.followup.send(f"Added tech {tech_name} to the tech market.")
			else:
				await itx.followup.send(f"Tech already exists!")
		except Exception as e:
			await itx.followup.send(f"[LOG]: <add_item> ERROR CODE 0: {e}")
		
	except Exception as e:
		# Log server-side and notify the user cleanly
		msg = f"[LOG]: <add_item> ERROR CODE 1: {type(e).__name__}: {e}"
		print(msg)
		await itx.followup.send(msg)

async def setup(bot:commands.Bot):
	await bot.add_cog(Debug(bot))		# Add debug cog
	bot.tree.add_command(market)	# Register group
	print("[cogs.cmds] cog added... current tree: ", [c.qualified_name for c in bot.tree.get_commands()])