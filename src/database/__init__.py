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
	get_table_asc,
	add_bal,
	add_res,
	remove_user_object,
	add_economy,
	add_item,
	add_tech,
	get_table_row,
	get_user_table_asc,
	get_inventory_item,
	remove_object,
	item_to_inv,
	econ_to_inv,
	tech_to_inv
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
	"get_table_asc",
	"get_user_table_asc",
	"add_bal",
	"add_res",
	"remove_user_object",
	"add_economy",
	"add_item",
	"add_tech",
	"get_table_row",
	"get_inventory_item",
	"remove_object",
	"item_to_inv",
	"econ_to_inv",
	"tech_to_inv"
]