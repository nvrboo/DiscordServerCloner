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

clone_options = {
    'clean_emojis': False,
    'clone_emojis': False,

    'clean_roles': True,
    'clone_roles': True,

    'clean_channels': True,
    'clone_categories': True,
    'clone_text_channels': True,
    'clone_voice_channels': True,
    'clone_forum_channels': True,
    'clone_stage_channels': True,

    'set_icon': True,
    'set_banner': True,
    'edit_settings': True,
    'enable_community': True,
    'edit_guild_channel_settings': True,
}
