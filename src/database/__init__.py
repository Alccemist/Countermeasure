"""
INFORMATION

	The database folder is where all of our data-related content exists.
	__init__ shows us the initialization and indexing functions.
	Importing database does not create or modify our database; we should call the functions explicitly.
	
"""

from .data_handler import(
	connect_database,
	close,
	create_database,
	create_indices,
	add_user,
	remove_user,
	get_table,
	add_economy,
	add_item,
	add_tech
)

async def initialize_database():
	await create_database()
	await create_indices()

__all__ = [
	"connect_database",
	"close",
	"create_database",
	"create_indices",
	"initialize_database",
	"add_user",
	"remove_user",
	"get_table",
	"add_economy",
	"add_item",
	"add_tech"
]