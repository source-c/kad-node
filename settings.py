import os
import json
import logging
from logging import Logger
import logging.handlers as handlers

settings_file = '.settings.json'

# noinspection PyUnresolvedReferences
from logging import (
    CRITICAL,
    FATAL,
    ERROR,
    WARNING,
    WARN,
    INFO,
    DEBUG,
    NOTSET
)

KADNODE_GLOBAL_LOGGING_LEVEL = DEBUG

operational_mode = os.environ.get('KADNODE_OPERATIONAL_MODE')

def get_settings(file: str = None) -> dict:
    settings = {}
    file_name = file or settings_file

    if os.path.isfile(file_name):
        with open(file_name, 'r') as fd:
            settings = json.load(fd)

    return settings


def get_logger(name: str = None, level: int = KADNODE_GLOBAL_LOGGING_LEVEL) -> Logger:
    log_name = name or __file__
    log_level = level or KADNODE_GLOBAL_LOGGING_LEVEL

    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log = logging.getLogger(log_name)
    log.addHandler(handler)
    log.setLevel(log_level)

    settings = get_settings()
    if settings.get("logging") and settings['logging'].get("logfile"):
        log_handler = handlers.TimedRotatingFileHandler('kad-node.log', when='M', interval=1, backupCount=1)
        log.addHandler(log_handler)

    return log


__all__ = (
    'get_settings', 'get_logger',
    'KADNODE_GLOBAL_LOGGING_LEVEL',
    'CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'WARN', 'INFO', 'DEBUG', 'NOTSET',
)
