from psyion.ext.database import SQLiteResource

def create_backend(server, id, label, database, **kw):
    if server == 'sqlite3':
        return create_sqlite3_backend(id, label, database, **kw)


def create_sqlite3_backend(id, label, database, min=None, max=None, name=None):
    """
    Backend factory for creating database pools.
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


class DBViewer(SQLiteResource):
    meta = {
            'id': 'db_viewer',
            'label': 'Database Viewer Pool',
            'min': 4,
            'max': 8
            }


# vim:set sw=4 sts=4 ts=4 et tw=79:
