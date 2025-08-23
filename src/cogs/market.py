	
"""
INFORMATION

		This contains all of our commands that users will execute. Table and data-related commands will often
	come with some kind of security check to avoid SQL injection or permission abuse.
	
"""

import database, discord, os, typing, utility_libs.utilities as utilities
from math import ceil # ==> For use in pagination
from discord import app_commands
from discord.ext import commands

""" [SETUP] """
DEBUG_GUILD_ID:int = int(os.getenv("DEBUG_GUILD_ID"))
ADMIN_ROLE_ID:int = int(os.getenv("ADMIN_ROLE_ID"))
OBJECTS_PER_PAGE:int = int(os.getenv("OBJECTS_PER_PAGE"))
log_utils = utilities.LoggingUtilities(True, True)
role_utils = utilities.RoleUtilities(admin_role_id=ADMIN_ROLE_ID)
renderer = utilities.RenderUtilities()

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
	guild_ids=[DEBUG_GUILD_ID],
)

# ==> [market] group
@market.command(name="economy_market", description="View available economies.")
async def economies(itx:discord.Interaction):
	log_utils.print_log("view_economies called")
	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetch our running client
	econs = await database.get_table_asc(bot.db, "economy_market", "economy_income")
	embeds = [] # ==> i.e. our pages

	if not econs:
		return await itx.followup.send("No economies found...", ephemeral = True)
	
	for i in range(0,len(econs), OBJECTS_PER_PAGE):
		chunk = econs[i:i+OBJECTS_PER_PAGE]
		# ==> We'll need to manually chunk things here before displaying data.
		embed = discord.Embed(title="Economies", color=MARKET_COLORS['economy_market'])
		for obj in chunk:
			embed.add_field(
				name=f"{obj["name"]}",
				value=f"__Income__\n*{obj["economy_income"]:,}  :coin:*",
				inline=False
				)
		embed.set_footer(text=f"Page {i//OBJECTS_PER_PAGE+1} of {ceil(len(econs)/OBJECTS_PER_PAGE)}") # Regarding the +1: recall 0-indexing.
		embeds.append(embed)
	
	view = renderer.Paginator(embeds=embeds)
	await itx.followup.send(embed=view.initial, view=view)

@market.command(name="item_market", description="View the item market.")
async def items(itx:discord.Interaction):
	log_utils.print_log("view_items called")
	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetch our running client
	items = await database.get_table_asc(bot.db, "item_market", "cost")
	embeds = [] # ==> i.e. our pages

	if not items:
		return await itx.followup.send("No items found...", ephemeral = True)
	
	for i in range(0,len(items), OBJECTS_PER_PAGE):
		chunk = items[i:i+OBJECTS_PER_PAGE]
		# ==> We'll need to manually chunk things here before displaying data.
		embed = discord.Embed(title="Item Market", color=MARKET_COLORS['item_market'])
		for item in chunk:
			embed.add_field(
				name=f"{item["cost"]:,} :coin: — {item["name"]}",
				value=f"\n\"{item["description"]}\"",
				inline=False
				)
		embed.set_footer(text=f"Page {i//OBJECTS_PER_PAGE+1} of {ceil(len(items)/OBJECTS_PER_PAGE)}") # Regarding the +1: recall 0-indexing.
		embeds.append(embed)
	
	view = renderer.Paginator(embeds=embeds)
	await itx.followup.send(embed=view.initial, view=view)
	
@market.command(name="tech_market", description="View available technology.")
async def technology(itx:discord.Interaction):
	log_utils.print_log("view_tech called")
	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetch our running client
	techs = await database.get_table_asc(bot.db, "tech_market", "cost")
	embeds = [] # ==> i.e. our pages

	if not techs:
		return await itx.followup.send("No tech found...", ephemeral = True)
	
	for i in range(0,len(techs), OBJECTS_PER_PAGE):
		chunk = techs[i:i+OBJECTS_PER_PAGE]
		# ==> We'll need to manually chunk things here before displaying data.
		embed = discord.Embed(title="Tech Market", color=MARKET_COLORS['tech_market'])
		for tech in chunk:
			embed.add_field(
				name=f"{tech["cost"]:,} :alembic: — {tech["name"]}",
				value=f"\n\"{tech["description"]}\"",
				inline=False
				)
		embed.set_footer(text=f"Page {i//OBJECTS_PER_PAGE+1} of {ceil(len(techs)/OBJECTS_PER_PAGE)}") # Regarding the +1: recall 0-indexing.
		embeds.append(embed)
	
	view = renderer.Paginator(embeds=embeds)
	await itx.followup.send(embed=view.initial, view=view)

# ==> [add] group. For admin use only
@market.command(name="add_economy")
async def add_economy(
	itx:discord.Interaction,
	name:str,
	economy_income:int
	):
	if not role_utils.has_admin(itx.user.roles,ADMIN_ROLE_ID):
		await itx.followup.send("Command failed.")
		await role_utils.err_not_admin(itx=itx)
		return
	try:
		await itx.response.defer()
		bot = typing.cast(commands.Bot, itx.client)
		try:
			item = await database.add_economy(bot.db,name,economy_income)
			if item:
				await itx.followup.send(f"Added status \"{name}\" to the economy market.")
			else:
				await itx.followup.send(f"Economy status already exists!")
		except Exception as e:
			await itx.followup.send(f"[ERR]: <add_obj> {type(e).__name__}: {e}")
		
	except Exception as e:
		# Log server-side and notify the user cleanly
		msg = f"[ERR]: <add_obj> {type(e).__name__}: {e}"
		print(msg)
		await itx.followup.send(msg)
	
@market.command(name="add_item")
async def add_item(
	itx:discord.Interaction,
	name:str,
	desc:typing.Optional[str],
	cost:int,
	req_tech:typing.Optional[str]
	):
	if not role_utils.has_admin(itx.user.roles,ADMIN_ROLE_ID):
		await itx.followup.send("Command failed.")
		await role_utils.err_not_admin(itx=itx)
		return
	try:
		await itx.response.defer()
		bot = typing.cast(commands.Bot, itx.client)
		try:
			item = await database.add_item(db=bot.db,name=name,desc=desc,cost=cost,req_tech=req_tech)
			if item:
				await itx.followup.send(f"Added item \"{name}\" to the item market.")
			else:
				await itx.followup.send(f"Item already exists!")
		except Exception as e:
			await itx.followup.send(f"[ERR]: <add_obj> {type(e).__name__}: {e}")
		
	except Exception as e:
		# Log server-side and notify the user cleanly
		msg = f"[ERR]: <add_obj> ERROR CODE 1: {type(e).__name__}: {e}"
		print(msg)
		await itx.followup.send(msg)

@market.command(name="add_tech")
async def add_tech(
	itx:discord.Interaction,
	name:str,
	desc:typing.Optional[str],
	tech_income:typing.Optional[int],
	cost:int,
	req_tech:typing.Optional[str]
	):
	if not role_utils.has_admin(itx.user.roles,ADMIN_ROLE_ID):
		await itx.followup.send("Command failed.")
		await role_utils.err_not_admin(itx=itx)
		return
	
	# Handle optional args:
	desc = None if not desc else desc
	tech_income = 0 if not tech_income else tech_income
	req_tech = None if not req_tech else req_tech

	print(f"Desc: {desc}, tech_inc: {tech_income}, reqtech: {req_tech}")

	try:
		await itx.response.defer()
		bot = typing.cast(commands.Bot, itx.client)
		try:
			item = await database.add_tech(bot.db,name,desc,tech_income,cost,req_tech)
			if item:
				await itx.followup.send(f"Added tech \"{name}\" to the tech market.")
			else:
				await itx.followup.send(f"Tech already exists!")
		except Exception as e:
			await itx.followup.send(f"[LOG]: <add_obj> ERROR CODE 0: {type(e).__name__}: {e}")
		
	except Exception as e:
		# Log server-side and notify the user cleanly
		msg = f"[LOG]: <add_obj> ERROR CODE 1: {type(e).__name__}: {e}"
		print(msg)
		await itx.followup.send(msg)

# ==> [remove] group. For admin use only
@market.command(name="delete_object")
@app_commands.choices(markets=[
	app_commands.Choice(name="Economy",		value="economy_market"),
	app_commands.Choice(name="Items",		value="item_market"),
	app_commands.Choice(name="Technology",	value="tech_market"),
])
async def delete_object(
	itx:discord.Interaction,
	markets:app_commands.Choice[str],
	object_name:str,
	):
	print("[LOG]: remove_object called...")
	if not role_utils.has_admin(itx.user.roles,ADMIN_ROLE_ID):
		await role_utils.err_not_admin(itx=itx)
		return
	try:
		await itx.response.defer()
		bot = typing.cast(commands.Bot, itx.client)
		try:
			rem = await database.remove_object(bot.db,markets.value,"name",object_name)
			if rem:
				await itx.followup.send(f"Removed object {object_name} from {markets.value}.")
			else:
				await itx.followup.send(f"Object doesn't exist!")
		except Exception as e:
			await itx.followup.send(f"[LOG]: <remove_object> ERROR CODE 0: {e}")
		
	except Exception as e:
		# Log server-side and notify the user cleanly
		msg = f"[LOG]: <remove_object> ERROR CODE 1: {type(e).__name__}: {e}"
		print(msg)
		await itx.followup.send(msg)
	
# ==> [transaction] group.

# ECONOMY HAS BEEN REMOVED IN FAVOR OF ECONOMIC STATES ASSIGNED BY MODS.
# potentially in the future, maybe our bot can read and assign player economic states based on rolls or other attributes.

@market.command(name="buy_item")
async def buy_item(itx:discord.Interaction, name:str, qty:int):
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetches the running client
	user = itx.user
	log_utils.print_log(f"buy_item called by {user.name} with args name: <{name}>, qty: <{qty}>")

	await itx.response.defer()
	if qty <= 0:
		await itx.followup.send("You can't buy nothing!")
		return

	# Get item, plr info
	try:
		itemRow = await database.get_table_row(
			db=bot.db,
			table_name="item_market",
			pk_col="name",	# column to look through in SQL table
			pk_val=name		# the value to match
		)
		if not itemRow:
			await itx.followup.send("No matching item found...")
			return
		plrRow = await database.get_table_row(
			db=bot.db,
			table_name="users",
			pk_col="user_id",	# column to look through in SQL table
			pk_val=user.id		# the value to match
		)
		if not plrRow:
			await itx.followup.send("No user found...")
			return
		plrTec = await database.get_user_table_asc(
			bot.db,
			"user_tech",
			user.id,
			"tech_income"
		)
		if not plrTec:
			log_utils.print_debug("No user tech found...")

		# Check if player has tech
		req = itemRow.get("req_tech")
		has_req = (not req) or any(t.get("name") == req for t in plrTec)

		if has_req:
			# Handle transaction
			log_utils.print_debug(f"Item cost: {itemRow['cost']}, Plr bal: {plrRow['balance']}")
			if itemRow['cost']*qty <= plrRow['balance']:
				log_utils.print_debug(f"Deducting {itemRow['cost']*qty} from player...")
				await database.add_bal(bot.db, user, -itemRow['cost']*qty)
				await database.item_to_inv(db=bot.db, item_name=name, user_id=user.id, quantity=qty)
				await itx.followup.send(f"Bought {qty} of {name} for {itemRow['cost']*qty} :coin:!")
			else:
				await itx.followup.send("Not enough money!")
		else:		
			await itx.followup.send(f"Missing required tech <{req}>.")
			log_utils.print_debug(f"{user.name} lacks the required tech <{req}>")

	except Exception as e:
		log_utils.print_log(f"[ERR]: {type(e).__name__}: {e}")
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")

@market.command(name="sell_item")
async def sell_item(itx:discord.Interaction, name:str, qty:int):
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetches the running client
	user = itx.user
	log_utils.print_log(f"sell_item called by {user.name} with args name: <{name}>, qty: <{qty}>")
	
	await itx.response.defer()

	if qty <= 0:
		await itx.followup.send("You can't sell nothing!")
		return

	# Get item, plr info
	try:
		itemRow = await database.get_table_row(
			db=bot.db,
			table_name="item_market",
			pk_col="name",	# column to look through in SQL table
			pk_val=name		# the value to match
		)
		if not itemRow:
			await itx.followup.send("No matching item found...")
		plrRow = await database.get_table_row(
			db=bot.db,
			table_name="users",
			pk_col="user_id",	# column to look through in SQL table
			pk_val=user.id		# the value to match
		)
		if not plrRow:
			await itx.followup.send("No user found...")
		invRow = await 	database.get_inventory_item(bot.db, user.id, name)
		if not invRow:
			await itx.followup.send(f"No item in inventory found. Do you have {name}?")
		log_utils.print_debug(f"Attempting to remove {qty} of {name} from {user.name}'s inventory...")

	# Handle transaction
		log_utils.print_debug(f"Item cost: {itemRow['cost']}, Plr bal: {plrRow['balance']}")
		if invRow['quantity'] >= qty:
			# Using item_to_inv to subtract
			await database.item_to_inv(db=bot.db, item_name=name, user_id=user.id, quantity=-qty)
			await database.add_bal(bot.db, user, itemRow['cost']*qty)
			await itx.followup.send(f"Sold {qty} of {name} for {itemRow['cost']*qty} :coin:!")
		else:
			await itx.followup.send(f"Not enough {name}!")
	
	except Exception as e:
		log_utils.print_log(f"[ERR]: {type(e).__name__}: {e}")
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")

@market.command(name="research")
async def research_tech(itx:discord.Interaction, tech:str):
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetches the running client
	user = itx.user
	log_utils.print_log(f"research called by {user.name} with args name: <{tech}>")

	await itx.response.defer()

	# Get tech, plr info
	try:
		techRow = await database.get_table_row(
			db=bot.db,
			table_name="tech_market",
			pk_col="name",	# column to look through in SQL table
			pk_val=tech		# the value to match
		)
		if not techRow:
			await itx.followup.send("No matching item found...")
			return
		plrRow = await database.get_table_row(
			db=bot.db,
			table_name="users",
			pk_col="user_id",	# column to look through in SQL table
			pk_val=user.id		# the value to match
		)
		if not plrRow:
			await itx.followup.send("No user found...")
			return
		plrTec = await database.get_user_table_asc(
			bot.db,
			"user_tech",
			user.id,
			"tech_income"
		)
		if not plrTec:
			log_utils.print_debug("No user tech found...")
		
		# Check if player has tech
		req = techRow.get("req_tech")
		has_req = (not req) or any(t.get("name") == req for t in plrTec)

		if has_req:
			# Handle transaction
			log_utils.print_debug(f"Tech cost: {techRow['cost']}, Plr res: {plrRow['research']}")
			if techRow['cost'] <= plrRow['research']:
				log_utils.print_debug(f"Deducting {techRow['cost']} from player...")
				await database.add_res(bot.db, itx.user, -techRow['cost'])
				await database.tech_to_inv(db=bot.db, tech_name=tech, user_id=user.id)
				await itx.followup.send(f"Researched {tech} for {techRow['cost']} :alembic:!")
			else:
				await itx.followup.send("Not enough RP!")
		else:		
			await itx.followup.send(f"Missing required tech <{req}>.")
			log_utils.print_debug(f"{user.name} lacks the required tech <{req}>")

	except Exception as e:
		log_utils.print_log(f"[ERR]: {type(e).__name__}: {e}")
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")


@market.command(name="use_item", description="Use your items. Admins can use others'.")
async def use_item(itx:discord.Interaction, user:discord.User, item_name:str, qty:int):
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetches the running client
	caller = itx.user
	log_utils.print_log(f"use_item called by {caller} with args name: <{item_name}>, qty: <{qty}>")

	# Admin check if our user isn't using their own items
	if caller.id != user.id:
		if not role_utils.has_admin(caller.roles, ADMIN_ROLE_ID):
			await itx.followup.send("Command failed.")
			await role_utils.err_not_admin(itx=itx)
			return
	
	await itx.response.defer()

	if qty <= 0:
		await itx.followup.send("You can't use nothing!")
		return

	# Get item, plr info
	try:
		itemRow = await database.get_table_row(
			db=bot.db,
			table_name="item_market",
			pk_col="name",	# column to look through in SQL table
			pk_val=item_name		# the value to match
		)
		if not itemRow:
			await itx.followup.send("No matching item found...")
		plrRow = await database.get_table_row(
			db=bot.db,
			table_name="users",
			pk_col="user_id",	# column to look through in SQL table
			pk_val=user.id		# the value to match
		)
		if not plrRow:
			await itx.followup.send("No user found...")
		invRow = await 	database.get_inventory_item(bot.db, user.id, item_name)
		if not invRow:
			await itx.followup.send(f"No item in inventory found. Do you have {item_name}?")
		log_utils.print_debug(f"Attempting to remove {qty} of {item_name} from {user.name}'s inventory...")

	# Handle transaction
		log_utils.print_debug(f"Item cost: {itemRow['cost']}, Plr bal: {plrRow['balance']}")
		if invRow['quantity'] >= qty:
			# Using item_to_inv to subtract
			await database.item_to_inv(db=bot.db, item_name=item_name, user_id=user.id, quantity=-qty)
		
		await itx.followup.send(f"Used {qty} of {item_name}!")
	
	except Exception as e:
		log_utils.print_log(f"[ERR]: {type(e).__name__}: {e}")
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")

async def setup(bot:commands.Bot):
	await bot.add_cog(Debug(bot))		# Add debug cog
	bot.tree.add_command(market)	# Register group
	print("[cogs.market] added... current tree: ", [c.qualified_name for c in bot.tree.get_commands()])