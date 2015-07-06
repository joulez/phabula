import os
import sqlite3
from stat import (
        S_ISDIR,
        S_ISREG,
        ST_MODE
        )
from urllib.parse import urljoin

from psyion.resources import (
        ChameleonTemplates,
        ChameleonTemplate,
        map_directory_tree
        )

from psyion.media import types as media_types

from psyion.predicates import request_methods
from psyion.sessions import CookieSession
from psyion.nodes import Node
from psyion.utils import SignedSerializer

from reform import HTMLBasicForm

from .resources import *
from .database.backends import create_backend

ROOT = '/'

__import__ = ('setup')

local_dir = os.path.dirname(__file__)

class Templates(metaclass=ChameleonTemplates):
    meta = {
            'dir': os.path.join(local_dir, 'templates'),
            'id': 'templates',
            'label': 'Chameleon Templates'
            }


def _register(app, router, base_path, **config):
    """
    Resource and node attachments and mappings.
    """
    predicates = config['predicates']
#    _signin_resource(app, router, base_path, predicates)
    _base_resource(app, router, base_path, predicates)
    #_listing_resource(app, router, base_path, predicates)
    #_item_resource(app, router, base_path, predicates)
#    _add_item_resource(app, router, base_path, predicates)
    _static_resources(app, router, base_path, predicates)

#def _listing_resource(app, router, base_path, predicates):
#    path = urljoin(base_path, 'list')
#    node = app.get_node(router, path, 'list')
#    app.registry.mappings.add(node, (ListItems, predicates))

def _static_resources(app, router, base_path, predicates):
    base_map = urljoin(base_path, 'assets')
    base_dir = os.path.join(local_dir, 'assets')
    base_node = app.get_node(router, base_map, 'phabula_assets')

    _static_directory_trees(app, router, base_dir, base_map, base_node,
            predicates)

def _static_directory_trees(app, router, base_dir, base_map, base_node, predicates):
    mappings = app.registry.mappings
    
    js_dir = os.path.join(base_dir, 'javascript')
    js_map = urljoin(base_map+'/', 'js')
    js_node = app.get_node(router, js_map, 'javascript_libraries')
    
    mootools_node = app.get_node(router, js_map+'/mootools.js', 'mootools')
    mappings.add(mootools_node, (Mootools, predicates))


    ck_dir = os.path.join(js_dir, 'ckeditor')

    map_directory_tree(router, mappings, js_node, ck_dir, 
            '^.*(.js|.css|.md|.png)',
            enable_cache=True,
            enable_hash=True,
            enable_alt=False,
            alt='//cdn.ckeditor.com/4.4.7/standard')

def _item_resource(app, router, base_path, predicates):
    pat = ':re:.(\d{0,10})$'
    path = urljoin(base_path, pat)
    node = app.get_node(router, path, node_id='item')
    app.registry.mappings.add(node, (item, predicates))

def _base_resource(app, router, base_path, predicates):
    app.registry.mappings.add(app.get_node(router, base_path, 'phab.root'),
            (root, predicates))

def _signin_resource(app, router, base_path, predicates):
    SigninForm.init()
    predicates.append(request_methods({'POST', 'GET', 'HEAD'}))
    app.registry.mappings.add(app.get_node(router, urljoin(base_path, 
        'signin'), 'signin'), (SigninForm, predicates))

    #app.registry.mappings.add(app.get_node(router, urljoin(base_path, 
    #    'signin'), 'signin'), (signin, predicates))

def reg_list_items(app, router, base_path, backend, **config):
    predicates = config['predicates']

    path = urljoin(base_path, 'list')

    node = app.get_node(router, path, 'view_list')

    item_resource = listitems(backend)

    app.registry.mappings.add(node, (item_resource, predicates))

    path = urljoin(base_path, 'item/:re:^.\d*')

    node = app.get_node(router, path, 'view_item')

    app.registry.mappings.add(node, (item_resource, predicates))



def reg_add_item(app, router, base_path, formbase, serializer, **config):
    predicates = config.get('predicates')

    path = urljoin(base_path, 'add')

    resource = additem(formbase, serializer)

    predicates.append(request_methods({'POST', 'GET', 'HEAD'}))

    app.registry.mappings.add(app.get_node(router, path, 'add_item'), 
            (resource, predicates))



def setup_db(app, config):
    predicates = config.get('predicates', [])
    database = config.get('database')
    if not os.path.exists(database):
        basedir = os.path.dirname(database)
        if not os.path.exists(basedir):
            os.makedirs(basedir)

    if not os.path.exists(database):
        print('No database found. Generating database file.')
        DDL = os.path.join(local_dir, 'database', 'DDL.sql')
        with open(DDL, 'r') as f:
            with sqlite3.connect(database) as conn:
                cursor = conn.cursor()
                cursor.executescript(f.read())
                cursor.execute('INSERT INTO app (name) VALUES'
                        ' (?)',(app.name,))
                conn.commit()
    else:
        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE app SET last_access = current_timestamp')
            conn.commit()


def setup_sessions(app, config):
    app.registry.sessions.add('phab.id', CookieSession)
    app.registry.sessions.add('pha_sess', CookieSession)


def setup(app, path=None, host_maps=None, template_dir=None, 
        backend=None, lang='en-US', **config):
    secret = config.get('secret', '')

    template_dir = template_dir or os.path.join(local_dir, 'templates')

    database = config['database']

    setup_db(app, config)
    setup_sessions(app, config)
    
    dbmodifier = create_backend('sqlite3', 'dbmodifier', 
            'Database Modify Pool', 
            database=database, 
            min=3, max=4)

    dbviewer = create_backend('sqlite3', 'dbviewier', 
            'Database View Pool', 
            database=database,
            min=3, max=4)

    serializer = SignedSerializer(secret)

    formbase = create_formbase(dbmodifier, serializer)

    path = path or ROOT

    base_path = path if path.endswith('/') else path+'/'

    resources = app.registry.resources

    router = app.get_router(host_maps) or app.create_router('phabula',
            host_maps=host_maps)

    resources.add(Templates)

    _register(app, router, base_path, **config)

    reg_list_items(app, router, base_path, 
            backend=dbmodifier, 
            serializer=serializer,
            **config)
    reg_add_item(app, router, base_path,
            formbase=formbase,
            serializer=serializer, 
            **config)
    return app


# vim:set sw=4 sts=4 ts=4 et tw=79:
