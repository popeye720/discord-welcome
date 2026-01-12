from .mongo import db


jtc_col = db["join_to_create"]
ticket_col = db["tickets"]
reactionrole_col = db["reaction_roles"]
autotrigger_col = db["auto_triggers"]
greetings_col = db["greetings"] 
autorole_col = db["auto_roles"]

freegames_col = db["free_games"]

ytnotify_col = db["ytnotify"]
ytnotify_col.create_index(
    [("guild_id", 1), ("yt_channel_id", 1)],
    unique=True
)

scheduled_embeds_col = db["scheduled_embeds"]
scheduled_embeds_col.create_index(
    [("guild_id", 1), ("schedule_id", 1)],
    unique=True
)

fungames_col = db["fun_games"]
fungames_col.create_index("guild_id", unique=True)

serverstats_col = db["server_stats"]
serverstats_col.create_index("guild_id", unique=True)

forms_col = db["forms"]
form_responses_col = db["form_responses"]

forms_col.create_index("guild_id", unique=True)
form_responses_col.create_index([("guild_id", 1), ("user_id", 1)], unique=True)



antilinks_col = db["anti_links"]
antilinks_col.create_index("guild_id", unique=True)



antispam_col = db["anti_spam"]
antispam_col.create_index("guild_id", unique=True)



streammode_col = db["stream_mode"]
streammode_col.create_index("guild_id", unique=True)

audiodown_col = db["audio_downloader"]
audiodown_col.create_index("guild_id", unique=True)

search_col = db["search_config"]
search_col.create_index("guild_id", unique=True)

autorenamer_col = db["auto_rename"]
autorenamer_col.create_index("guild_id", unique=True)

privatevc_col = db["private_vc"]
privatevc_col.create_index("guild_id", unique=True)


guilds_col = db["guilds"]
guilds_col.create_index("guild_id", unique=True)


blacklisted_guilds_col = db["blacklisted_guilds"]
blacklisted_guilds_col.create_index("guild_id", unique=True)