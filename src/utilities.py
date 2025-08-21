"""
INFORMATION

	Utilities contains some helper functions, like checking if a player is an admin.

"""
import discord

async def is_role(user:discord.Member, role_id:int) -> bool:
	return any(r.id == role_id for r in user.roles)