import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TOKEN") # replace it with your token as a "string". Example: TOKEN = "abc"
original_guild_id = os.environ.get("ORIGINAL_GUILD_ID") # change it to id of the original server. Example: original_guild_id = 1234567890
new_guild_id = os.environ.get("NEW_GUILD_ID") # change it to id of the new server. Example: new_guild_id = 1234567890

if original_guild_id is not None:
    original_guild_id = int(original_guild_id)
if new_guild_id is not None:
    new_guild_id = int(new_guild_id)
