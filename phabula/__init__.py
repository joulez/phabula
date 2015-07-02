import os
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

from reform import HTMLBasicForm

from .resources import *
from .database.backends import create_backend

ROOT = '/'

__import__ = ('setup')

_local_dir = os.path.dirname(__file__)

class Templates(metaclass=ChameleonTemplates):
    meta = {
            'dir': os.path.join(_local_dir, 'templates'),
            'id': 'templates',
            'label': 'Chameleon Templates'
            }


def _register(app, router, base_path, predicates):
    """
    Resource and node attachments and mappings.
    """
    _signin_resource(app, router, base_path, predicates)
    _base_resource(app, router, base_path, predicates)
    #_listing_resource(app, router, base_path, predicates)
    #_item_resource(app, router, base_path, predicates)
    _add_item_resource(app, router, base_path, predicates)
    _static_resources(app, router, base_path, predicates)


def _register_db(app, router, base_path, predicates):
    database = '/tmp/test.sqlite3'
    dbmodifier = create_backend('sqlite3', database,
            'dbmodifier', 'Database Modify Pool', min=3, max=4)
    dbviewer = create_backend('sqlite3', database,
            'dbviewier', 'Database View Pool', min=3, max=4)
    path = urljoin(base_path, 'list')
    node = app.get_node(router, path, 'view_list')
    item_resource = listitems(dbmodifier)
    app.registry.mappings.add(node, (item_resource, predicates))
    path = urljoin(base_path, 'item/:re:^.\d*')
    node = app.get_node(router, path, 'view_item')
    app.registry.mappings.add(node, (item_resource, predicates))

    

#def _listing_resource(app, router, base_path, predicates):
#    path = urljoin(base_path, 'list')
#    node = app.get_node(router, path, 'list')
#    app.registry.mappings.add(node, (ListItems, predicates))

def _static_resources(app, router, base_path, predicates):
    base_map = urljoin(base_path, 'assets')
    base_dir = os.path.join(_local_dir, 'assets')
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

def _add_item_resource(app, router, base_path, predicates):
    AddItem.init()
    predicates.append(request_methods({'POST', 'GET', 'HEAD'}))
    app.registry.mappings.add(app.get_node(router, urljoin(base_path,
        'add'), 'add'), (AddItem, predicates))
    return 

def setup(app, path=None, host_maps=None, template_dir=None, 
        backend=None, predicates=[], lang='en-US'):

    template_dir = template_dir or os.path.join(_local_dir, 'templates')

    #add id session
    app.registry.sessions.add('phab.id', CookieSession)
    #add default session
    app.registry.sessions.add('pha_sess', CookieSession)

    path = path or ROOT
    base_path = path if path.endswith('/') else path+'/'


    resources = app.registry.resources
    router = app.get_router(host_maps) or app.create_router('phabula', host_maps=host_maps)
    resources.add(Templates)
    #DBModifier.set_args(database='/tmp/test.sqlite2')
    _register(app, router, base_path, predicates)
    _register_db(app, router, base_path, predicates)
    return app


# vim:set sw=4 sts=4 ts=4 et tw=79:
