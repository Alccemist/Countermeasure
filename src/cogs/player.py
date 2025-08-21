"""
INFORMATION

	This is our player interaction library. It addresses the automatic events in our server.
	
"""
import database, discord, os, typing, utility_libs.utilities as utilities
from discord import app_commands
from discord.ext import commands
from utility_libs.utilities import LoggingUtilities, RenderUtilities as renderer
from math import ceil

""" [SETUP] """
DEBUG_GUILD_ID:int = int(os.getenv("DEBUG_GUILD_ID"))
ADMIN_ROLE_ID:int = int(os.getenv("ADMIN_ROLE_ID"))
OBJECTS_PER_PAGE:int = int(os.getenv("OBJECTS_PER_PAGE"))
PAYOUT_STEP:int = int(os.getenv("PAYOUT_STEP"))
role_utils = utilities.RoleUtilities(admin_role_id=ADMIN_ROLE_ID)
log_utils = LoggingUtilities(True,True)

# For our embeds.
PLAYER_COLORS = {
	"statistics":		discord.Color.dark_teal(),
	"user_economy":		discord.Color.gold(),
	"user_inventories":	discord.Color.dark_grey(),
	"user_tech":		discord.Color.blue(),
}

# ~~ [ADMIN FAMILY] ~~
# For admins only.
admin = app_commands.Group(
	name="admin",
	description = "Perform admin actions",
	guild_ids=[DEBUG_GUILD_ID],
)

@admin.command(name="add_user_to_database", description="Add a member if they aren't in the db.")
async def add_user_to_database(itx:discord.Interaction, user:discord.Member):
	log_utils.print_log(f"add_user_to_database called")
	await itx.response.defer()
	try:
		if not role_utils.has_admin(itx.user.roles, ADMIN_ROLE_ID):
			await role_utils.err_not_admin(itx=itx)
			return
	except Exception as e:
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")
	try:
		bot = typing.cast(commands.Bot, itx.client)
		await database.add_user(bot.db,user)
		await itx.followup.send(f"Added {user.name} to database...") 
	except Exception as e:
		log_utils.print_log(f"[ERR]: {type(e).__name__}: {e}")
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")
		return
	return

@admin.command(name="add_object_to_user", description="Add an object from available markets to a user.")
@app_commands.choices(markets=[
	app_commands.Choice(name="Economy",		value="economy_market"),
	app_commands.Choice(name="Items",		value="item_market"),
	app_commands.Choice(name="Technologies",value="tech_market")
])
async def add_object_to_user(
	itx:discord.Interaction,
	markets:app_commands.Choice[str],
	quantity:typing.Optional[int],
	object_name:str,
	user:discord.Member
	):
	log_utils.print_log("Called add_object_to_user")
	await itx.response.defer()
	try:
		if not role_utils.has_admin(itx.user.roles, ADMIN_ROLE_ID):
			await role_utils.err_not_admin(itx=itx)
			return
		bot = typing.cast(commands.Bot, itx.client)

		if markets.value == "item_market":
			log_utils.print_debug("item market selected")
			await database.item_to_inv(db=bot.db, item_name=object_name, user_id=user.id, quantity=quantity)
			await itx.followup.send(f"{object_name} has been cloned to {user.name}'s inventory!")

		if markets.value == "economy_market":
			log_utils.print_debug("economy market selected")
			await database.econ_to_inv(db=bot.db, econ_name=object_name, user_id=user.id)
			await itx.followup.send(f"{object_name} has been cloned to {user.name}'s economy!")

		if markets.value == "tech_market":
			log_utils.print_debug("tech market selected")
			await database.tech_to_inv(db=bot.db, tech_name=object_name, user_id=user.id)
			await itx.followup.send(f"{object_name} has been cloned to {user.name}'s tech!")

	except Exception as e:
		log_utils.print_log(f"{type(e).__name__}: {e}")
		await itx.followup.send(f"{type(e).__name__}: {e}")

@admin.command(name="delete_object_from_user", description="Delete an object in a user's data.")
@app_commands.choices(inventory=[
	app_commands.Choice(name="Economy",		value="user_economy"),
	app_commands.Choice(name="Items",		value="user_inventories"),
	app_commands.Choice(name="Technologies",value="user_tech")
])
async def delete_object_from_user(
	itx:discord.Interaction,
	inventory:app_commands.Choice[str],
	object_name:str,
	user:discord.Member
	):
	log_utils.print_log("Called delete_object_from_user")
	await itx.response.defer()
	try:
		if not role_utils.has_admin(itx.user.roles, ADMIN_ROLE_ID):
			await role_utils.err_not_admin(itx=itx)
			return
		bot = typing.cast(commands.Bot, itx.client)

		if inventory.value == "user_inventories":
			log_utils.print_debug("user inventories selected")
			await database.remove_user_object(bot.db, 'user_inventories', user, 'name', object_name)
			await itx.followup.send(f"{object_name} has been deleted from {user.name}'s inventory!")

		if inventory.value == "user_economy":
			log_utils.print_debug("user economy selected")
			await database.remove_user_object(bot.db, 'user_economy', user, 'name', object_name)
			await itx.followup.send(f"{object_name} has been deleted from {user.name}'s economy!")

		if inventory.value == "user_tech":
			log_utils.print_debug("user tech selected")
			await database.remove_user_object(bot.db, 'user_tech', user, 'name', object_name)
			await itx.followup.send(f"{object_name} has been deleted from {user.name}'s tech!")

	except Exception as e:
		log_utils.print_log(f"{type(e).__name__}: {e}")
		await itx.followup.send(f"{type(e).__name__}: {e}")

@admin.command(name="add_balance_to_user", description="Add (or subtract from) to a user's balance.")
async def add_balance_to_user(itx:discord.Interaction, user:discord.Member, qty:int):
	await itx.response.defer()
	try:
		if not role_utils.has_admin(itx.user.roles, ADMIN_ROLE_ID):
			await role_utils.err_not_admin(itx=itx)
			return
	except Exception as e:
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")
	try:
		bot = typing.cast(commands.Bot, itx.client)
		await database.add_bal(bot.db, user, qty)
		await itx.followup.send(f"Added {qty} :coin: to {user.name}")
	except Exception as e:
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")

@admin.command(name="add_research_to_user", description="Add (or subtract from) to a user's research.")
async def add_research_to_user(itx:discord.Interaction, user:discord.Member, qty:int):
	await itx.response.defer()
	try:
		if not role_utils.has_admin(itx.user.roles, ADMIN_ROLE_ID):
			await role_utils.err_not_admin(itx=itx)
			return
	except Exception as e:
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")
	try:
		bot = typing.cast(commands.Bot, itx.client)
		await database.add_res(bot.db, user, qty)
		await itx.followup.send(f"Added {qty} RP to {user.name}")
	except Exception as e:
		await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")

# ~~ [view FAMILY] ~~
# Used to browse through player information
player = app_commands.Group(
	name="player",
	description = "Browse and interact with player information.",
	guild_ids=[DEBUG_GUILD_ID],
)

@player.command(name="view_statistics", description="View player statistics. Other players are admin-only.")
async def statistics(
	itx:discord.Interaction,
	user:discord.User	
	):
	await itx.response.defer()

	if user != itx.user:
		if not role_utils.has_admin(itx.user.roles, ADMIN_ROLE_ID):
			await itx.followup.send("Command failed.")
			await role_utils.err_not_admin(itx=itx)
			return

	try:
		bot = typing.cast(commands.Bot, itx.client)
		user_stats = await database.get_table_row(bot.db, "users", "user_id", user.id)

		if not user_stats:
			return await itx.followup.send(f"ERR: {user.name} has no user_stats... Contact an admin!")
		emb = discord.Embed(title="Statistics", color=PLAYER_COLORS["statistics"])
		emb.add_field(name="Balance", value=f"{user_stats['balance']:,} :coin:", inline=False)
		emb.add_field(name="Research", value=f"{user_stats['research']:,} :alembic:", inline=False)
		await itx.followup.send(embed=emb)
	except Exception as e:
		log_utils.print_log(f"ERROR: {e}")
		return
	return

@player.command(name="view_economy", description="View player economy. Other players are admin-only.")
async def economy(
	itx:discord.Interaction,
	user:discord.User	
	):
	log_utils.print_log(f"inventory of {user.name} called by {itx.user.name}")

	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetch our running client
	inv = await database.get_user_table_asc(bot.db, "user_economy", user.id, "economy_income")
	embeds = [] # ==> i.e. our pages

	if not inv:
		return await itx.followup.send("No economy found...", ephemeral = True)
	
	for i in range(0,len(inv), OBJECTS_PER_PAGE):
		chunk = inv[i:i+OBJECTS_PER_PAGE]
		# ==> We'll need to manually chunk things here before displaying data.
		embed = discord.Embed(title=f"{user.name}'s Economy", color=discord.Color.dark_grey())
		for item in chunk:
			embed.add_field(
				name=item['name'],
				value=f"{item['economy_income']:,} :coin: / {PAYOUT_STEP}d",
				inline=False
				)
		embed.set_footer(text=f"Page {i//OBJECTS_PER_PAGE+1} of {ceil(len(inv)/OBJECTS_PER_PAGE)}") # Regarding the +1: recall 0-indexing.
		embeds.append(embed)
	
	view = renderer.Paginator(embeds=embeds)
	await itx.followup.send(embed=view.initial, view=view)

@player.command(name="view_items", description="View player inventory. Other players are admin-only.")
async def inventory(
	itx:discord.Interaction,
	user:discord.User	
	):
	log_utils.print_log(f"inventory of {user.name} called by {itx.user.name}")

	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetch our running client
	inv = await database.get_user_table_asc(bot.db, "user_inventories", user.id, "quantity")
	embeds = [] # ==> i.e. our pages

	if not inv:
		return await itx.followup.send("No inventory found...", ephemeral = True)
	
	for i in range(0,len(inv), OBJECTS_PER_PAGE):
		chunk = inv[i:i+OBJECTS_PER_PAGE]
		# ==> We'll need to manually chunk things here before displaying data.
		embed = discord.Embed(title=f"{user.name}'s Inventory", color=discord.Color.dark_grey())
		for item in chunk:
			embed.add_field(
				name=item['name'],
				value=f"{item['quantity']:,}",
				inline=False
				)
		embed.set_footer(text=f"Page {i//OBJECTS_PER_PAGE+1} of {ceil(len(inv)/OBJECTS_PER_PAGE)}") # Regarding the +1: recall 0-indexing.
		embeds.append(embed)
	
	view = renderer.Paginator(embeds=embeds)
	await itx.followup.send(embed=view.initial, view=view)

@player.command(name="view_tech", description="View player tech. Other players are admin-only.")
async def technology(
	itx:discord.Interaction,
	user:discord.User	
	):
	log_utils.print_log(f"inventory of {user.name} called by {itx.user.name}")

	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client) # ==> Fetch our running client
	inv = await database.get_user_table_asc(bot.db, "user_tech", user.id, "tech_income")
	embeds = [] # ==> i.e. our pages

	if not inv:
		return await itx.followup.send("No tech found...", ephemeral = True)
	
	for i in range(0,len(inv), OBJECTS_PER_PAGE):
		chunk = inv[i:i+OBJECTS_PER_PAGE]
		# ==> We'll need to manually chunk things here before displaying data.
		embed = discord.Embed(title=f"{user.name}'s Technology", color=discord.Color.dark_grey())
		for item in chunk:
			embed.add_field(
				name=item['name'],
				value=f"{item['tech_income']:,} :alembic: / {PAYOUT_STEP}d",
				inline=False
				)
		embed.set_footer(text=f"Page {i//OBJECTS_PER_PAGE+1} of {ceil(len(inv)/OBJECTS_PER_PAGE)}") # Regarding the +1: recall 0-indexing.
		embeds.append(embed)
	
	view = renderer.Paginator(embeds=embeds)
	await itx.followup.send(embed=view.initial, view=view)

# ~~ [P2P FAMILY] ~~
# Used to interact with another player's information

@player.command(name="transact", description="Transact with another player.")
@app_commands.choices(options=[
	app_commands.Choice(name="Give", value="give"),
	app_commands.Choice(name="Pay",  value="pay")
])
async def transact(
	itx:discord.Interaction,
	options:app_commands.Choice[str],
	recipient:discord.User,
	item:typing.Optional[str],
	quantity:int
	):
	log_utils.print_log(f"transact called: {itx.user.name} wants to {options.value} {quantity} {item} to {recipient.name}")
	await itx.response.defer()
	bot = typing.cast(commands.Bot, itx.client)

	if quantity <= 0:
		await itx.followup.send("You can't transact nothing!")
		return

	if options.value == "give":
		# Use /use logic, but we must also add item to recipient
		# Get item, plr info
		try:
			itemRow = await database.get_table_row(
				db=bot.db,
				table_name="item_market",
				pk_col="name",	# column to look through in SQL table
				pk_val=item		# the value to match
			)
			if not itemRow:
				await itx.followup.send("No matching item found...")
			recRow = await database.get_table_row(
				db=bot.db,
				table_name="users",
				pk_col="user_id",	# column to look through in SQL table
				pk_val=recipient.id	# the value to match
			)
			if not recRow:
				await itx.followup.send("No recipient found...")
			invRow = await 	database.get_inventory_item(bot.db, itx.user.id, item)
			if not invRow:
				await itx.followup.send(f"No item in inventory found. Do you have {item}?")
			log_utils.print_debug(f"Attempting to remove {quantity} of {item} from {itx.user.name}'s inventory...")

		# Handle transaction
			if invRow['quantity'] >= quantity:
				# Using item_to_inv to subtract
				log_utils.print_debug(f"Subtracting from {itx.user.name}'s inventory:")
				await database.item_to_inv(db=bot.db, item_name=item, user_id=itx.user.id, quantity=-quantity)
				log_utils.print_debug(f"Passing to {recipient.name}'s inventory:")
				await database.item_to_inv(db=bot.db, item_name=item, user_id=recipient.id, quantity=quantity)
			
			await itx.followup.send(f"Gave {quantity} of {item} to {recipient.name}!")
		
		except Exception as e:
			log_utils.print_log(f"[ERR]: {type(e).__name__}: {e}")
			await itx.followup.send(f"[ERR]: {type(e).__name__}: {e}")

	if options.value == "pay":
		# use /buy balance aspect, but we must also add curr. to recipient
		return



async def setup(bot:commands.Bot):	# Add debug cog
	bot.tree.add_command(player)
	bot.tree.add_command(admin)
	print("[cogs.player] added... current tree: ", [c.qualified_name for c in bot.tree.get_commands()])