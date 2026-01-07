from .mongo import db


jtc_col = db["join_to_create"]
ticket_col = db["tickets"]
reactionrole_col = db["reaction_roles"]
autotrigger_col = db["auto_triggers"]
greetings_col = db["greetings"] 
autorole_col = db["auto_roles"]
guilds_col = db["guilds"]
freegames_col = db["free_games"]

ytnotify_col = db["ytnotify"]

ytnotify_col.create_index(
    [("guild_id", 1), ("yt_channel_id", 1)],
    unique=True
)






serverstats_col = db["server_stats"]
serverstats_col.create_index("guild_id", unique=True)