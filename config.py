from configparser import ConfigParser

config = ConfigParser()
config.read("config.ini")


API_ID = int(config.get("telethon", "api_id"))
API_HASH = config.get("telethon", "api_hash")

SUDO_USERS = [int(u[1]) for u in config.items("admins")]

REDIS_URL = config.get("database", "redis")

BLOCKLIST = config.get("blocklist", "symbols").upper().split(" ")