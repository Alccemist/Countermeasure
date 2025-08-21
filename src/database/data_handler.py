"""
INFORMATION

	This is our data handler. It's where the actual meat & potatoes of the db system lie.
	The time-valued attributes follow INTEGER Unix format. Scheduler will also obey this.
	
"""

""" [IMPORTS] """
# For Discord API interaction... do we rly need this?
import discord
import aiosqlite

""" [TABLE NAMES] - For convenience.
users
user_economy
user_inventories
user_tech
economy_market
item_market
tech_market
"""

""" [SETUP] """
DB_PATH = "src/database/Countermeasure.db"

WHITELISTED_TABLES = {
	"economy_market",
	"item_market",
	"tech_market"
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
		await db.execute("PRAGMA foreign_keys = ON;")
		await db.execute("""
			CREATE TABLE IF NOT EXISTS users(
					user_id INTEGER PRIMARY KEY,
					username TEXT,
					balance INTEGER DEFAULT 0,
					research INTEGER DEFAULT 0,
					auto_collect INTEGER DEFAULT 0,
					last_collect TEXT DEFAULT NULL,
					auto_research INTEGER DEFAULT 0,
					last_research TEXT DEFAULT NULL	
			)
		""")

	# user economy table. Contains the tech that the user has unlocked
		await db.execute("""
			CREATE TABLE IF NOT EXISTS user_economy(
					user_id INTEGER NOT NULL,
					economy_name TEXT NOT NULL,
					PRIMARY KEY (user_id, economy_name),
					FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
					FOREIGN KEY (economy_name) REFERENCES economy_market(economy_name) ON DELETE CASCADE
			)
		""")

	# user inventories table. Independent from users since inventories can get large!
		await db.execute("""
			CREATE TABLE IF NOT EXISTS user_inventories(
					user_id INTEGER NOT NULL,
					item_name TEXT NOT NULL,
					quantity INTEGER DEFAULT 0 CHECK(quantity >= 0),
					PRIMARY KEY (user_id, item_name),
					FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
					FOREIGN KEY (item_name) REFERENCES item_market(item_name) ON DELETE CASCADE
			)
		""")

	# user tech table. Contains the tech that the user has unlocked
		await db.execute("""
			CREATE TABLE IF NOT EXISTS user_tech(
					user_id INTEGER NOT NULL,
					tech_name TEXT NOT NULL,
					PRIMARY KEY (user_id, tech_name),
					FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
					FOREIGN KEY (tech_name) REFERENCES tech_market(tech_name) ON DELETE CASCADE
			)
		""")

	# economy_market Table. We store the levels of economy for unlocking here.
	# --> Note that the cost of the economy MUST be unlocked thu FACTORIES!!
	# --> Has an option for prerequisite economies.
		await db.execute("""
			CREATE TABLE IF NOT EXISTS economy_market(
					economy_name TEXT PRIMARY KEY NOT NULL,
					economy_income INTEGER,
					economy_cost INTEGER,
					req_economy TEXT
			)
		""")

	# item_market Table. where items for sale exist.
	# Many items will require unlockable "Tech" roles to buy. 
	# ==> Uses some currency. NOT same as tech cost
	# --> I plan to make a check where if not req_role, then we can go ahead and try to buy. If req_role, then check if player has role, then try to buy, etc etc...
	# --> No duplicate names allowed!
		await db.execute("""
			CREATE TABLE IF NOT EXISTS item_market(
					item_name TEXT PRIMARY KEY NOT NULL,
					description TEXT,
					item_cost INTEGER,
					amt_in_stock INTEGER CHECK(amt_in_stock >= 0),
					max_stock INTEGER CHECK(max_stock >= 0),
					req_tech TEXT
			)
		""")

	
	# tech_market Table. where techs for unlocking exist.
	# Similar to item market, but no supply attributes. Retains required roles for "tech tree" style gameplay.
	# ==> tech cost is like "research pts"
		await db.execute("""
			CREATE TABLE IF NOT EXISTS tech_market(
					tech_name TEXT PRIMARY KEY NOT NULL,
					description TEXT,
					tech_cost INTEGER,
					req_tech TEXT
			)
		""")

		await db.commit()

# TODO: POLISH INDICES SEARCHUP CASES
# --> BELOW IS A DRAFT... TO BE POLISHED

# Foreign keys ensure that each key matches an existing users.user_id. If the user_id is removed, then # all affiliated data is removed.
# --> We"ll create indices now for lookup efficiency via CREATE INDEX IF NOT EXISTS idx_<table>_<column> ON <table>(<column>);

async def create_indices() -> None:
	async with aiosqlite.connect(DB_PATH) as db:
		await db.execute("PRAGMA foreign_keys=ON;")

		# Item possession i.e. "who owns this item?"
		# ==> REMOVED. PK IN ITEM INVENTORY IS ALREADY (user_id, item_name)

		# Foreign Key indexes for frequent per-user fetching
		await db.execute("CREATE INDEX IF NOT EXISTS idx_econ_user ON user_economy(user_id);")
		await db.execute("CREATE INDEX IF NOT EXISTS idx_inv_user ON user_inventories(user_id);")
		await db.execute("CREATE INDEX IF NOT EXISTS idx_tech_user ON user_tech(user_id);")

		# Last collected timestamps for economy
		await db.execute("""
			CREATE INDEX IF NOT EXISTS idx_users_last_collect
			ON users(last_collect) WHERE last_collect IS NOT NULL;
		""")

		# Last researched timestamps for research
		await db.execute("""
			CREATE INDEX IF NOT EXISTS idx_users_last_research
			ON users(last_research) WHERE last_research IS NOT NULL;
		""")

		await db.commit()


""" [UTILITY FUNCTIONS] """

""" ~~ [add FAMILY] ~~
	This is where our add_<object> functions are written.
"""
# [add_economy]
# ==> Adds an item to the item market.
async def add_economy(db:aiosqlite.Connection, economy_name:str, economy_income:str, cost:int, req_economy:str) -> bool:
	c = await db.execute(
		"INSERT OR IGNORE INTO economy_market(economy_name, economy_income, economy_cost, req_economy) VALUES (?, ?, ?, ?)",
		(economy_name,economy_income,cost,req_economy),
	)
	await db.commit()
	    # rowcount = 1 means we successfully inserted; 0 means the user already existed
	return c.rowcount == 1

# [add_item]
# ==> Adds an item to the item market.
async def add_item(db:aiosqlite.Connection, item_name:str, desc:str, cost:int, amt:int, max:int, req_tech:str) -> bool:
	c = await db.execute(
		"INSERT OR IGNORE INTO item_market(item_name, description, item_cost, amt_in_stock, max_stock, req_tech) VALUES (?, ?, ?, ?, ?, ?)",
		(item_name,desc,cost,amt,max,req_tech),
	)
	await db.commit()
	    # rowcount = 1 means we successfully inserted; 0 means the user already existed
	return c.rowcount == 1

# [add_tech]
# ==> Adds a tech to the technology market.
async def add_tech(db:aiosqlite.Connection, tech_name:str, desc:str, tech_cost:int, req_tech:str) -> bool:
	c = await db.execute(
		"INSERT OR IGNORE INTO tech_market(tech_name, description, tech_cost, req_tech) VALUES (?, ?, ?, ?)",
		(tech_name,desc,tech_cost,req_tech),
	)
	await db.commit()
	    # rowcount = 1 means we successfully inserted; 0 means the user already existed
	return c.rowcount == 1



""" ~~ [get FAMILY] ~~
	This is our family of functions that return information — commonly tables...
"""
# [get_table]
# ==> Returns a whitelisted table. Receives its name.. See cogs/cmds.py for its use...
async def get_table(db:aiosqlite.Connection, table_name:str):
	if table_name not in WHITELISTED_TABLES:
		raise ValueError("Disallowed table...")
	
	db.row_factory = aiosqlite.Row # "row_factory" lets our rows behave like dicts. Using .Row to avoid manual indexing like row[0]
	async with db.execute(f"SELECT * FROM {table_name}") as c:
		rows = await c.fetchall()
		return [dict(row) for row in rows] # list[dict]
	


""" ~~ [user FAMILY] ~~
	These functions modify user information in the database.
"""
# [add_user]
# ==> To be used in bot.py to register a user to the DB.
async def add_user(db:aiosqlite.Connection, user:discord.User) -> bool:
	c = await db.execute(
		"INSERT OR IGNORE INTO users(user_id, username) VALUES (?, ?)",
		(user.id, user.name),
	)
	await db.commit()
	    # rowcount = 1 means we successfully inserted; 0 means the user already existed
	return c.rowcount == 1

# [remove_user]
# ==> To be used in bot.py to remove a user from the DB
async def remove_user(db:aiosqlite.Connection, user:discord.User):
	async with aiosqlite.connect(DB_PATH) as db:
		print(f"Received db & user... {db.name}, {user.name} <{user.id}>")
		
		c = await db.execute("DELETE FROM users WHERE user_id = ?", (user.id))
		await db.commit()
		return c.rowcount > 0 