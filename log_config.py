from pathlib import Path

from decouple import AutoConfig

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

config = AutoConfig(search_path="resources/.env")

OFFICE_EMAIL = config('OFFICE_EMAIL', default='')
OFFICE_PASSWORD = config('OFFICE_PASSWORD', default='')
WARNING_EMAIL = config('WARNING_EMAIL', default='')
LEVUS_INFO_EMAIL = config('LEVUS_INFO_EMAIL', default='')

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO"
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "standard",
            "level": "INFO",
            "filename": f"{log_dir}/pux.log",
            "encoding": "utf-8"
        },
        "smtp_warning": {
            "class": "logging.handlers.SMTPHandler",
            "formatter": "standard",
            "level": "WARNING",
            "mailhost": ("smtp.gmail.com", 587),
            "fromaddr": OFFICE_EMAIL,
            "toaddrs": [WARNING_EMAIL, LEVUS_INFO_EMAIL],
            "subject": "Log Warning Alert",
            "credentials": (OFFICE_EMAIL, OFFICE_PASSWORD),
            "secure": ()
        }
    },
    "loggers": {
        "pux-button": {
            "handlers": ["console", "file", "smtp_warning"],
            "level": "INFO"
        }
    }
}
