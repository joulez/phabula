from .resources import Data
from .backends import default_backend
def setup(app, path=None, host_maps=None, backend=default_backend, predicates={}):
    backend = backend or default_backend
    path = path or '/'

    resources = app.registry.resources
    mappings = app.registry.mappings

    routers = app.get_router(host_maps)
    node = app.get_node(router, path, ':phabula:')

    Data.set_backend(backend)
    resources.add(Data)
    mappings.add(node, (Data, predicates))


# vim:set sw=4 sts=4 st=4 et tw=79:
