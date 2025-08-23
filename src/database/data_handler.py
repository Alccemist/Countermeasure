"""
INFORMATION

	This is our data handler. It's where the actual meat & potatoes of the db system lie.
	Time-valued attributes should follow UTC.
	
"""

""" [IMPORTS] """
import aiosqlite, discord, typing
from utility_libs.utilities import LoggingUtilities

""" [TABLE NAMES] - For our convenience.
users
user_economy
user_inventories
user_tech
economy_market
item_market
tech_market
schedule
"""

""" [SETUP] """
DB_PATH = "database/Countermeasure.db"
LogUtil = LoggingUtilities(True,True)

WHITELISTED_TABLES = {
	"users",
	"user_economy",
	"user_inventories",
	"user_tech",
	"economy_market",
	"item_market",
	"tech_market",
	"schedule"
}

""" [INITIALIZATION FUNCTIONS] """
# [database connect & close ] --> a wrapper used to connect to/close our database. Saves need to import aiosqlite
async def connect_database():
	db = await aiosqlite.connect(DB_PATH)
	await db.execute("PRAGMA foreign_keys = ON;")
	db.row_factory = aiosqlite.Row
	return db

async def close(db:aiosqlite.Connection):
	await db.close()

async def create_database() -> None:
	async with aiosqlite.connect(DB_PATH) as db:
		# users Table
		await db.execute("""
			CREATE TABLE IF NOT EXISTS users(
				user_id INTEGER PRIMARY KEY,
				username TEXT,
				balance INTEGER DEFAULT 0,
				research INTEGER DEFAULT 0
			)
		""")

	# user economy table. Contains the economies that our user has unlocked.
		await db.execute("""
			CREATE TABLE IF NOT EXISTS user_economy(
				user_id INTEGER NOT NULL,
				name TEXT NOT NULL,
				economy_income INTEGER,
				PRIMARY KEY (user_id, name),
				FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
				FOREIGN KEY (name) REFERENCES economy_market(name) ON DELETE CASCADE
			)
		""")

	# user inventories table. Independent from users since inventories can get large!
		await db.execute("""
			CREATE TABLE IF NOT EXISTS user_inventories(
				user_id INTEGER NOT NULL,
				name TEXT NOT NULL,
				quantity INTEGER DEFAULT 0 CHECK(quantity >= 0),
				PRIMARY KEY (user_id, name),
				FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
				FOREIGN KEY (name) REFERENCES item_market(name) ON DELETE CASCADE
			)
		""")

	# user tech table. Contains the tech that the user has unlocked.
	# Tech may have an income assigned to it. This contributes to a player's research during payouts.
		await db.execute("""
			CREATE TABLE IF NOT EXISTS user_tech(
				user_id INTEGER NOT NULL,
				name TEXT NOT NULL,
				tech_income INTEGER,
				PRIMARY KEY (user_id, name),
				FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
				FOREIGN KEY (name) REFERENCES tech_market(name) ON DELETE CASCADE
			)
		""")

	# economy_market Table. We store the levels of economy here. These are to be assigned by mods.
		await db.execute("""
			CREATE TABLE IF NOT EXISTS economy_market(
				name TEXT PRIMARY KEY NOT NULL,
				economy_income INTEGER
			)
		""")

	# item_market Table. where items for sale exist.
	# Many items will require unlockable "Tech" roles to buy. 
	# ==> Uses currency. NOT same as research
	# --> I plan to make a check where if not req_role, then we can go ahead and try to buy. If req_role, then check if player has role, then try to buy, etc etc...
	# --> No duplicate names allowed!
	# ==> Cost CAN be negative. This adds credit to a player.
		await db.execute("""
			CREATE TABLE IF NOT EXISTS item_market(
				name TEXT PRIMARY KEY NOT NULL,
				description TEXT,
				cost INTEGER,
				req_tech TEXT
			)
		""")

	
	# tech_market Table. where techs for unlocking exist.
	# Similar to item market, but no supply attributes. Retains required roles for "tech tree" style gameplay.
	# ==> tech cost is like "research pts"
		await db.execute("""
			CREATE TABLE IF NOT EXISTS tech_market(
				name TEXT PRIMARY KEY NOT NULL,
				description TEXT,
				tech_income INTEGER,
				cost INTEGER,
				req_tech TEXT
			)
		""")

	# schedule Table. Where scheduler data lives. Follows YYYY-MM-DD UTC format
		await db.execute("""
			CREATE TABLE IF NOT EXISTS schedule(
				run_date TEXT PRIMARY KEY,
				status TEXT NOT NULL CHECK(status IN ('started','complete','failed')),
				started_at TEXT NOT NULL, -- datetime('now')
				finished_at TEXT, -- set when completed OR failed
				error_msg TEXT -- Optional failure note				
			)
		""")

		await db.commit()
		LogUtil.print_log("DB Tables Created")

async def create_indices() -> None:
	async with aiosqlite.connect(DB_PATH) as db:
		await db.execute("PRAGMA foreign_keys=ON;")

		# Item possession i.e. "who owns this item?"
		# ==> REMOVED. PK IN ITEM INVENTORY IS ALREADY (user_id, name)

		# Foreign Key indexes for frequent per-user fetching
		await db.execute("CREATE INDEX IF NOT EXISTS idx_econ_user ON user_economy(user_id);") # user in econ
		await db.execute("CREATE INDEX IF NOT EXISTS idx_inv_user ON user_inventories(user_id);") # user in inventory
		await db.execute("CREATE INDEX IF NOT EXISTS idx_tech_user ON user_tech(user_id);") # user in tech

		await db.commit()


""" [UTILITY FUNCTIONS] """

""" ~~ [add_<object> FAMILY] ~~
	This is where our add_<object>-type functions are written.
"""
# [add_economy]
# ==> Adds an item to the item market.
async def add_economy(db:aiosqlite.Connection, name:str, economy_income:str) -> bool:
	c = await db.execute(
		"INSERT OR IGNORE INTO economy_market(name, economy_income) VALUES (?, ?)",
		(name,economy_income),
	)
	await db.commit()
	    # rowcount = 1 means we successfully inserted; 0 means the user already existed
	return c.rowcount == 1

# [add_item]
# ==> Adds an item to the item market.
async def add_item(db:aiosqlite.Connection, name:str, desc:str, cost:int, req_tech:str) -> bool:
	c = await db.execute(
		"INSERT OR IGNORE INTO item_market(name, description, cost, req_tech) VALUES (?, ?, ?, ?)",
		(name,desc,cost,req_tech),
	)
	await db.commit()
	    # rowcount = 1 means we successfully inserted; 0 means the user already existed
	return c.rowcount == 1

# [add_tech]
# ==> Adds a tech to the technology market.
async def add_tech(db:aiosqlite.Connection, name:str, desc:str, tech_income:int, cost:int, req_tech:str) -> bool:
	c = await db.execute(
		"INSERT OR IGNORE INTO tech_market(name, description, tech_income, cost, req_tech) VALUES (?, ?, ?, ?, ?)",
		(name, desc, tech_income, cost, req_tech),
	)
	await db.commit()
	    # rowcount = 1 means we successfully inserted; 0 means the user already existed
	return c.rowcount == 1

""" ~~ [get FAMILY] ~~
	This is our family of functions that return information. Commonly tables...
"""
# [get_table_asc]
# ==> Returns a whitelisted table. Receives a name and the column to ascend.
async def get_table_asc(db:aiosqlite.Connection, table:str, col:str):
	if table not in WHITELISTED_TABLES:
		raise ValueError("Disallowed table...")
	
	db.row_factory = aiosqlite.Row # "row_factory" lets our rows behave like dicts. Using .Row to avoid manual indexing like row[0]
	async with db.execute(f"SELECT * FROM {table} ORDER BY {col} ASC") as c:
		rows = await c.fetchall()
		return [dict(row) for row in rows] # list[dict]
	
# [get_user_table_asc]
# ==> Returns an ascending table with only one user's objects.
async def get_user_table_asc(db:aiosqlite.Connection, table:str, user_id:int, col:str):
	LogUtil.print_debug("get_user_table_asc called")
	if table not in WHITELISTED_TABLES:
		raise ValueError("Disallowed table...")
	
	db.row_factory = aiosqlite.Row # "row_factory" lets our rows behave like dicts. Using .Row to avoid manual indexing like row[0]
	async with db.execute(f"SELECT * FROM {table} WHERE user_id = ? ORDER BY {col} ASC", (user_id,)) as c:
		rows = await c.fetchall()
		return [dict(row) for row in rows] # list of dictionaries, i.e. list[dict]

# [get_table_row]
# ==> Returns a dictionary of the row.. We search by primary key.
async def get_table_row(db:aiosqlite.Connection, table_name:str, pk_col:str, pk_val:typing.Any) -> dict|None:
	LogUtil.print_debug("Called get_table_row")
	if table_name not in WHITELISTED_TABLES:
		LogUtil.print_debug(f"{table_name} NOT WHITELISTED")
		raise ValueError("Disallowed table...")
	
	db.row_factory = aiosqlite.Row 
	# "row_factory" lets our rows behave like dicts. Using .Row to avoid manual indexing like row[0]
	query = f"SELECT * FROM {table_name} WHERE {pk_col} = ?"
	# ==> The asertisk means "all columns" in the row.
	# ==> Using ? param to avoid sql injection attacks.

	async with db.execute(query, (pk_val,)) as c: # recall we want a tuple type...
		LogUtil.print_debug(f"Selecting from {table_name} where {pk_col} = {pk_val!r}")
		# So in this case, we want pk_col to match the value (e.g. 'superpower', 'small economy')
		row = await c.fetchone()

	if row:
		row_dict = dict(row)
		LogUtil.print_debug(f"Fetched row -> dict {row_dict}")
		return row_dict
	return None

async def get_inventory_item(db:aiosqlite.Connection, user_id:int, item_name:str) -> dict|None:
	LogUtil.print_debug("Called get_inventory_item")
	db.row_factory = aiosqlite.Row 

	query = f"SELECT * FROM user_inventories WHERE user_id = ? AND name = ?"
	args = (user_id, item_name)
	async with db.execute(query, args) as c:
		item_row = await c.fetchone()

	if item_row:
		item_dict = dict(item_row)
		LogUtil.print_debug(f"Fetched row -> dict {item_dict}")			
		return item_dict
	return None

""" ~~ [user FAMILY] ~~
	These functions handle user information in the database.
"""
# [add_user]
# ==> To be used in bot.py & scheduler to register a user to the DB user tables.
# ==> Returns the amount of rows added, or if none added, returns an error.
async def add_user(db:aiosqlite.Connection, user:discord.User):
	queries = [
		("INSERT OR IGNORE INTO users(user_id, username) VALUES (?, ?)", (user.id, user.name)),
		("INSERT OR IGNORE INTO user_economy(user_id) VALUES (?)", (user.id,)),
		("INSERT OR IGNORE INTO user_inventories(user_id) VALUES (?)", (user.id,)),
		("INSERT OR IGNORE INTO user_tech(user_id) VALUES (?)", (user.id,))
	]	

	sum_rows = 0
	for query, param in queries:
		c = await db.execute(query, param)
		sum_rows += c.rowcount
		# ==> row_ct tracks how many rows we've added. c.rowcount would only get our last insert's info.

	if sum_rows > 0:
		await db.commit()
		return sum_rows
	    # rowcount > 0 means we successfully inserted at least 1 row; 0 means the user is already in all tables
	else:
		raise ValueError(f"User {user.id} already exists in all tables!")

# [remove_user]
# ==> To be used in bot.py to remove a user from the DB
async def remove_user(db:aiosqlite.Connection, user:discord.User):
	async with aiosqlite.connect(DB_PATH) as db:
		LogUtil.print_log(f"Received db & user to remove... {db.name}, {user.name} <{user.id}>")
		
		c = await db.execute("DELETE FROM users WHERE user_id = ?", (user.id))
		await db.commit()
		return c.rowcount > 0 

# [add_bal]
# ==> Used to add a number to the user balance (we can add negatives)
async def add_bal(db:aiosqlite.Connection, user:discord.User, qty:int):
	LogUtil.print_debug(f"Adding {qty} to {user}'s balance...")
	try:
		await db.execute(
			f"""
				UPDATE users
				SET balance = balance + ? WHERE user_id = ?
			""",
			(qty, user.id)
		)
		await db.commit()
	except Exception:
		raise

# [add_res]
# ==> Used to add research to the user balance
async def add_res(db:aiosqlite.Connection, user:discord.Member, qty:int):
	LogUtil.print_debug(f"Adding {qty} to {user.name}'s research...")
	try:
		await db.execute(
			f"""
				UPDATE users
				SET research = research + ? WHERE user_id = ?
			""",
			(qty, user.id)
		)
		await db.commit()
	except Exception:
		raise

# [remove_user_object]
# ==> Removes an object from a user object table.
async def remove_user_object(db:aiosqlite.Connection, table_name:str, user:discord.Member, pk_col:str, pk_val:typing.Any) -> bool:
	query = f"DELETE FROM {table_name} WHERE {pk_col} = ? AND user_id = ?"
	c = await db.execute(query, (pk_val, user.id))
	await db.commit()
	return c.rowcount > 0



""" ~~ [OBJ-TO FAMILY] ~~
	These are used whenever we want to move an object from one table to another table that has matching columns.
	Some receive a user_id, like item_market -> user_inventories
	When creating OBJ-TO's: Be careful to match attributes (columns)!
"""
# [item_to_inv]
# ==> Copies an object from the item market to a user inventory.
async def item_to_inv(*, db:aiosqlite.Connection, item_name:str, user_id:int, quantity:int):
	LogUtil.print_log("Called item_to_inv")
	# ==> Check if User is registered:
	user_check = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
	if not await user_check.fetchone():
		raise ValueError(f"User ID {user_id} does not exist in users table.")
	# ==> Check if item exists
	item_market_check = await db.execute("SELECT 1 FROM item_market WHERE name = ?", (item_name,))
	if not await item_market_check.fetchone():
		raise ValueError(f"Item '{item_name}' does not exist in item_market.")
	item_inv_check = await db.execute("SELECT user_id, name FROM user_inventories WHERE user_id = ? AND name = ?", (user_id, item_name))
	
	if not quantity:
		raise ValueError("Missing quantity!")
	elif not await item_inv_check.fetchone():
		LogUtil.print_debug("User did not have item before. Inserting...")
		c = await db.execute(
			"INSERT OR IGNORE INTO user_inventories(user_id, name, quantity) VALUES (?, ?, ?)",
			(user_id, item_name, quantity)
		)
	else:
		c = await db.execute("""
			UPDATE user_inventories
			SET quantity = quantity + ? WHERE user_id = ? AND name = ?
		""", (quantity, user_id, item_name))
	if c.rowcount > 0:
		LogUtil.print_log(f"Copied {quantity} of {item_name} to user <{user_id}>")
		await db.commit()
	else:
		raise ValueError("Item not copied!")
	
# [econ_to_inv]
# ==> Copies an econ from economy_market to a user econ inventory.
async def econ_to_inv(*, db:aiosqlite.Connection, econ_name:str, user_id:int):
	LogUtil.print_log("Called econ_to_inv")
	db.row_factory = aiosqlite.Row # ==> To let our rows behave like dicts

	# ==> Check if User is registered:
	LogUtil.print_debug("Checking if user registered")
	user_check = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
	if not await user_check.fetchone():
		raise ValueError(f"User ID {user_id} does not exist in users table.")
	
	# ==> Check if econ exists by trying to select economy_income
	LogUtil.print_debug(f"SELECT * FROM economy_market WHERE name = {econ_name}")
	econ_income = await db.execute("SELECT * FROM economy_market WHERE name = ?", (econ_name,))
	income_row = await econ_income.fetchone()
	try:
		income_dict = dict(income_row)
		LogUtil.print_debug(f"Fetched {income_dict}")
	except:
		pass

	LogUtil.print_debug(f"SELECT * FROM user_economy WHERE user_id = {user_id} AND name = {econ_name}")
	econ_inv_check = await db.execute("SELECT * FROM user_economy WHERE user_id = ? AND name = ?", (user_id, econ_name))
	inv_row = await econ_inv_check.fetchone()
	try:
		inv_dict = dict(inv_row)
		LogUtil.print_debug(f"Fetched {inv_dict}")
	except:
		pass

	if not income_row:
		raise ValueError(f"Economy '{econ_name}' does not exist in economy_market.")

	LogUtil.print_log(f"We want to move {income_dict['name']} with magnitude {income_dict['economy_income']} to {user_id}'s economies.")
	
	if not inv_row:
		LogUtil.print_debug("User did not have econ before. Inserting...")
		await db.execute(
			"INSERT OR IGNORE INTO user_economy(user_id, name, economy_income) VALUES (?, ?, ?)",
			(user_id, econ_name, income_dict['economy_income'])
		)
		LogUtil.print_log(f"Copied {econ_name} to user <{user_id}>")
		await db.commit()
	else:
		raise ValueError("Economy not copied! The user may already have this economy.")

# [tech_to_inv]
# ==> Copies a tech from tech_market to a user tech inventory.
async def tech_to_inv(*, db:aiosqlite.Connection, tech_name:str, user_id:int):
	LogUtil.print_log("Called tech_to_inv")
	db.row_factory = aiosqlite.Row # ==> To let our rows behave like dicts

	# ==> Check if User is registered:
	LogUtil.print_debug("Checking if user registered")
	user_check = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
	if not await user_check.fetchone():
		raise ValueError(f"User ID {user_id} does not exist in users table.")
	
	# ==> Check if econ exists by trying to select economy_income
	LogUtil.print_debug(f"SELECT * FROM tech_market WHERE name = {tech_name}")
	tech_income = await db.execute("SELECT * FROM tech_market WHERE name = ?", (tech_name,))
	income_row = await tech_income.fetchone()
	try:
		income_dict = dict(income_row)
		LogUtil.print_debug(f"Fetched {income_dict}")
	except:
		pass

	LogUtil.print_debug(f"SELECT * FROM user_tech WHERE user_id = {user_id} AND name = {tech_name}")
	tech_inv_check = await db.execute("SELECT * FROM user_tech WHERE user_id = ? AND name = ?", (user_id, tech_name))
	inv_row = await tech_inv_check.fetchone()
	try:
		inv_dict = dict(inv_row)
		LogUtil.print_debug(f"Fetched {inv_dict}")
	except:
		pass

	if not income_row:
		raise ValueError(f"Technology '{tech_name}' does not exist in economy_market.")

	LogUtil.print_log(f"We want to move {income_dict['name']} with magnitude {income_dict['tech_income']} to {user_id}'s economies.")
	
	if not inv_row:
		LogUtil.print_debug("User did not have tech before. Inserting...")
		await db.execute(
			"INSERT OR IGNORE INTO user_tech(user_id, name, tech_income) VALUES (?, ?, ?)",
			(user_id, tech_name, income_dict['tech_income'])
		)
		LogUtil.print_log(f"Copied {tech_name} to user <{user_id}>")
		await db.commit()
	else:
		raise ValueError("Technology not copied! The user may already have this tech.")

""" ~~ [OBJECT FAMILY] ~~
	This is where our abstract object-level functions are written (meaning they are more versatile)
"""

# [remove_object]
# ==> Removes an object from a table.
async def remove_object(db:aiosqlite.Connection, table_name:str, pk_col:str, pk_val:typing.Any) -> bool:
	LogUtil.print_log(f"In {db}, {table_name}: Removing {pk_val} in {pk_col}...")
	query = f"DELETE FROM {table_name} WHERE {pk_col} = ?"
	c = await db.execute(query, (pk_val,)) # Again, using ? to avoid sql injection...
		# ==> NOTE: ? only replaces values, not identifies like table/col names
	await db.commit()
	return c.rowcount > 0

