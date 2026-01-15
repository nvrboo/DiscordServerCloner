import config
from cloner import ServerCloner

if __name__ == '__main__':
    if config.TOKEN is None or config.TOKEN == "":
        config.TOKEN = input("Enter your Discord Token: ")
    if config.original_guild_id is None:
        config.original_guild_id = int(input("Enter guild id you want to copy: "))
    if config.new_guild_id is None:
        config.new_guild_id = int(input("Enter guild id where you want to copy: "))
    cloner = ServerCloner(config.TOKEN, config.original_guild_id, config.new_guild_id)
    cloner.clone()
