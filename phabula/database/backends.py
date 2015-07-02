from psyion.ext.database import SQLiteResource

def create_backend(server, id, label, database, **kw):
    if server == 'sqlite3':
        return create_sqlite3_backend(id, label, database, **kw)
    elif server == 'postgres':
        raise NotImplementedError


def create_sqlite3_backend(id, label, database, min=None, max=None):
    """
    Backend factory for creating database pools with the sqlite3 database.
    """
    class DBResource(SQLiteResource):
        meta = {
                'id': id,
                'label': label,
                'min': min,
                'max' : max,
                'conn_args': {'database': database},
                'auto_initialize': True
            }
    return DBResource


def create_postgresql_backend(id, label, database, min=None, max=None):
    """
    Backend factory for creating database pools with the postgresql database.
    """
    class DBResource(PgSQLResource):
        meta = {
                'id': id,
                'label': label,
                'min': min,
                'max' : max,
                'conn_args': {'database': database},
                'auto_initialize': True
            }
    return DBResource


# vim:set sw=4 sts=4 ts=4 et tw=79:
