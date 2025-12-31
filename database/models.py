from .mongo import db

autorole_col = db["autorole"]
jtc_col = db["join_to_create"]
ticket_col = db["tickets"]
reactionrole_col = db["reaction_roles"]
autotrigger_col = db["auto_triggers"]

yt_notify_col = db["yt_notify"]
yt_last_col = db["yt_last"]
free_games_col = db["free_games_config"]