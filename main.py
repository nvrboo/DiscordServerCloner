import config
from cloner import ServerCloner

if __name__ == '__main__':
    if config.TOKEN is None or config.TOKEN == "":
        config.TOKEN = input("Enter your Discord Token: ")
    original_guild_id = int(input("Enter guild id you want to copy: "))
    new_guild_id = int(input("Enter guild id where you want to copy: "))
    cloner = ServerCloner(config.TOKEN, original_guild_id, new_guild_id)
    cloner.clone()
