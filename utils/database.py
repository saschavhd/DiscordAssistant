import pymongo
from pymongo import MongoClient
from utils.constants import MONGODB_API_KEY

cluster = MongoClient(MONGODB_API_KEY)
db = cluster['DiscordAssistantCluster']

DEFAULT_USER = {
    '_id': 0,
    'servers': {
        }
}

DEFAULT_SERVER = {
    '_id': 0,
    'prefix': '.',
    'banned_words': [],
    'roles': {
        'muted': 0,
        'birthday': 0
    },
    'counting': {
        'current': 1,
        'last_counter': 0
    },
    'channels': {
        'ignore': [],
        'ignore_exp': []
        },
    'polls': {},
    'role_managers': {},
    'events': {}
}



'''
DEFAULT_SERVER = {
    '_id': 0,
    'prefix': '.',
    'banned_words': [],
    'roles': {
        'muted': 0,
        'birthday': 0
    },
    'counting': {
        'last_counter': 0,
        'current': 1
    }
    'channels': {
        'ignore': [],
        'ignore_exp': [],
        'spawn': 0,
        'eject': 0,
        'log': 0,
        'birthday': 0,
        'counting': 0
        },
    'polls': {},
    'role_managers': {},
    'events': {}
}
'''
