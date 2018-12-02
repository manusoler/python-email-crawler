import logging

DEBUG = True 				# Whether or not to show DEBUG level messages
USE_COLORS = True 			# Whether or not colors should be used when outputting text
REMOVE_DDBB = True			# Whether or not remove existing ddbb when starting
DOMAINS_BLACKLIST = [		# Email domains that won't be included in the result
]

LOGGING = {						# dictConfig for output stream and file logging
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'console': {
            'format': '[%(asctime)s] %(levelname)s::%(module)s - %(message)s',
        },
        'file': {
            'format': '[%(asctime)s] %(levelname)s::(P:%(process)d T:%(thread)d)::%(module)s - %(message)s',
        },
    },

    'handlers': {
        'console': {
            'class': 'ColorStreamHandler.ColorStreamHandler',
            'formatter': 'console',
            'level': 'DEBUG',
            'use_colors': USE_COLORS,
        },
        'file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'file',
            'level': 'INFO',
            'when': 'midnight',
            'filename': 'logs/pycrawler.log',
                        'interval': 1,
                        'backupCount': 0,
                        'encoding': None,
                        'delay': False,
                        'utc': False,
        },
    },

    'loggers': {
        'crawler_logger': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True,
        },
    }
}
