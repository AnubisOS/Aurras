""" GENERAL SETTINGS """
NAME = "DATETIME"  # name of the plugin.  Used mostly in debugging
PRIORITY = 0  #! priority of the plugin - how it competes with other plugins sharing the same intents
ACCEPTED_INTENTS = ["get_date", "get_time"]  # list of all intents this plugin reacts to

""" PLUGIN SETTINGS """
DATE_FORMAT = "%B %d"
TIME_FORMAT = "%H:%M"
