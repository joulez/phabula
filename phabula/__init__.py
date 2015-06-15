import os
from urllib.parse import urljoin

from psyion.resources import (
        ChameleonTemplates,
        ChameleonTemplate
        )

from psyion.media import types as media_types

from psyion.predicates import request_methods
from psyion.sessions import CookieSession


from reform import HTMLBasicForm

from .resources import *

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

def _base_resource(app, router, base_path, predicates):
    app.registry.mappings.add(app.get_node(router, base_path, 'phab.root'),
            (root, predicates))



def _signin_resource(app, router, base_path, predicates):
    predicates.append(request_methods({'POST', 'GET', 'HEAD'}))
    app.registry.mappings.add(app.get_node(router, urljoin(base_path, 
        'signin'), 'signin'), (signin, predicates))

    return signin

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
    _register(app, router, base_path, predicates)
    return app


# vim:set sw=4 sts=4 ts=4 et tw=79:
