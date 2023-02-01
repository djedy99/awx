import psycopg2
import select
import logging
import time
import os
import signal

from contextlib import contextmanager

from django.conf import settings
from django.db import connection as pg_connection, OperationalError, Error

logger = logging.getLogger('awx.dispatch.init')

NOT_READY = ([], [], [])


def get_local_queuename():
    return settings.CLUSTER_HOST_ID


class PubSub(object):
    def __init__(self, conn):
        self.conn = conn

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
        if not self.conn.autocommit:
            raise RuntimeError('Listening for events can only be done in autocommit mode')

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
def pg_bus_conn(new_connection=False):
    '''
    Any listeners probably want to establish a new database connection,
    separate from the Django connection used for queries, because that will prevent
    losing connection to the channel whenever a .close() happens.

    Any publishers probably want to use the existing connection
    so that messages follow postgres transaction rules
    https://www.postgresql.org/docs/current/sql-notify.html
    '''
    conn = None
    retry_conn = False
    MAX_RETRIES = settings.DISPATCHER_DB_DOWNTOWN_TOLLERANCE
    POLL_SECONDS = int(settings.DISPATCHER_DB_DOWNTOWN_TOLLERANCE / 10)
    
    if new_connection:
        conf = settings.DATABASES['default']
        conn = psycopg2.connect(
            dbname=conf['NAME'], host=conf['HOST'], user=conf['USER'], password=conf['PASSWORD'], port=conf['PORT'], **conf.get("OPTIONS", {})
        )
        # Django connection.cursor().connection doesn't have autocommit=True on by default
        conn.set_session(autocommit=True)
    else:
        if pg_connection.connection is None:
            for retry_count in range(MAX_RETRIES):
                try:
                    pg_connection.connect()
                    conn = pg_connection.connection
                except (psycopg2.OperationalError, OperationalError, Error) as reconn_error:
                    logger.warning(f'Database unavailable. Retry with new connection in next {POLL_SECONDS} seconds. Attempt {retry_count}/{MAX_RETRIES}.')
                    time.sleep(POLL_SECONDS)
                    retry_conn = True
                else: 
                    if retry_conn:
                        logger.warning('Run dispatcher restart due to database connection loss and restore.')
                        os.kill(os.getppid(), signal.SIGTERM)
                    break
            else:
                raise RuntimeError(f'Could not connect to postgres afer {MAX_RETRIES} retries.')
        else:
            conn = pg_connection.connection

    pubsub = PubSub(conn)
    yield pubsub
    if new_connection:
        conn.close()
