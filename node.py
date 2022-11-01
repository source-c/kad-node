import asyncio
import random
import uuid
import json

from kademlia.network import Server
import settings as st

settings = st.get_settings()
log = st.get_logger('k-node')

typeset_native = [
    int,
    float,
    bool,
    str,
    bytes
]

typeset_supported = [
    object,
    uuid.UUID
]


def wrap_set_val_type(v):
    if type(v) in typeset_native:
        return v
    if type(v) in typeset_supported:
        if type(v) == uuid.UUID:
            return json.dumps({'_t': 'uuid', '_v': str(v)})
        if type(v) == object:
            return json.dumps(v)


def wrap_get_val_type(v):
    if type(v) in set(typeset_native) - {str}:
        return v
    try:
        obj = json.loads(v)
        if obj.get('_t') and obj['_t'] == 'uuid':
            obj = uuid.UUID(obj['_v'])
        return obj
    except Exception:
        return v


GRID_NODE_DEFAULT_PORT: int = 8690
GRID_NODE_DEFAULT_DEBUG_MODE: bool = True
GRID_NODE_ID_BIT_LENGTH: int = 128
GRID_STORAGE_DEFAULT_TTL: int = 604800  # i.e. 1 week

from kademlia.storage import IStorage
from collections import OrderedDict
from itertools import takewhile
import operator
import time


class DefaultStorage(IStorage):
    def __init__(self, ttl=GRID_STORAGE_DEFAULT_TTL):
        log.info("DefaultStorage init")
        self.data = OrderedDict()
        self.ttl = ttl

    def __setitem__(self, key, value):
        if key in self.data:
            del self.data[key]
        if value:
            self.data[key] = (time.monotonic(), value)
        self.cull()

    def cull(self):
        for _, _ in self.iter_older_than(self.ttl):
            self.data.popitem(last=False)

    def get(self, key, default=None):
        self.cull()
        if key in self.data:
            return self[key]
        return default

    def __getitem__(self, key):
        self.cull()
        return self.data[key][1]

    def __repr__(self):
        self.cull()
        return repr(self.data)

    def iter_older_than(self, seconds_old):
        min_birthday = time.monotonic() - seconds_old
        zipped = self._triple_iter()
        matches = takewhile(lambda r: min_birthday >= r[1], zipped)
        return list(map(operator.itemgetter(0, 2), matches))

    def _triple_iter(self):
        ikeys = self.data.keys()
        ibirthday = map(operator.itemgetter(0), self.data.values())
        ivalues = map(operator.itemgetter(1), self.data.values())
        return zip(ikeys, ibirthday, ivalues)

    def __iter__(self):
        self.cull()
        ikeys = self.data.keys()
        ivalues = map(operator.itemgetter(1), self.data.values())
        return zip(ikeys, ivalues)

    def __del__(self):
        log.info("DefaultStorage destroy")


class Node(object):

    def __init__(self,
                 id: int = None,
                 port: int = GRID_NODE_DEFAULT_PORT,
                 bshost: int = None,
                 bsport: int = None,
                 loop: asyncio.AbstractEventLoop = None):
        _bootstrap_node = (str(bshost), int(bsport)-1) if (bshost and bsport) else None
        _nodeid = str(id) if id else str(random.getrandbits(128))

        port = port if port else GRID_NODE_DEFAULT_PORT

        self.id = _nodeid
        self._server = Server(storage=DefaultStorage())
        self.loop = loop or asyncio.get_event_loop()

        self.loop.set_debug(GRID_NODE_DEFAULT_DEBUG_MODE)  # TODO: to config
        log.debug("init: %s", (port, _bootstrap_node))

        self.loop.run_until_complete(self._server.listen(port))

        if _bootstrap_node:
            self.loop.run_until_complete(self._server.bootstrap([_bootstrap_node]))

    def info(self) -> None:
        log.debug("%s %s", self.id, self._server)

    def set(self, k, v) -> bool:
        return self.loop.run_until_complete(self._server.set(k, wrap_set_val_type(v)))

    def get(self, k) -> object or None:
        return wrap_get_val_type(self.loop.run_until_complete(self._server.get(k)))

    def rem(self, k) -> None:
        import kademlia.utils as u
        self.loop.run_until_complete(self._server.set_digest(u.digest(k), None))

    def __del__(self):
        try:
            self._server.stop()
        except:
            log.warn("server already stopped")
            pass

        try:
            self.loop.close()
        except:
            log.warn("loop already closed")
            pass
