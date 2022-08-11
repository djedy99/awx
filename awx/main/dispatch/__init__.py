import select

from contextlib import contextmanager

from django.conf import settings
from django.db import connection as pg_connection


NOT_READY = ([], [], [])


def get_local_queuename():
    return settings.CLUSTER_HOST_ID


class PubSub(object):
    @property
    def conn(self):
        if pg_connection.connection is None:
            pg_connection.connect()
        return pg_connection.connection

    def listen(self, channel):
        with self.conn.cursor() as cur:
            cur.execute('LISTEN "%s";' % channel)

    def unlisten(self, channel):
        with self.conn.cursor() as cur:
            cur.execute('UNLISTEN "%s";' % channel)

    def notify(self, channel, payload):
        with self.conn.cursor() as cur:
            cur.execute('SELECT pg_notify(%s, %s);', (channel, payload))

    def events(self, select_timeout=5, yield_timeouts=False):
        while True:
            if select.select([self.conn], [], [], select_timeout) == NOT_READY:
                if yield_timeouts:
                    yield None
            else:
                self.conn.poll()
                while self.conn.notifies:
                    yield self.conn.notifies.pop(0)

    def close(self):
        self.conn.close()


@contextmanager
def pg_bus_conn():
    pubsub = PubSub()
    yield pubsub
