import os
import io
import time

from psyion.utils import (
        function_resource,
        random64,
        SignedSerializer
        )

from reform import (
        HTMLBasicForm, 
        PasswordInput, 
        EmailInput, 
        FileInput, 
        Button,
        HiddenInput,
        CheckBox,
        TextInput,
        TextArea,
        SelectInput,
        SelectOption
        )

from .defaults import default_context
from psyion import media
from psyion.resources import (
        Resource,
        DirectoryResource,
        IOFileResource,
        REQUIRED,
        DEFAULT
        )
from psyion.http import headers
from psyion.utils import logging

log = logging.getLogger(__name__)

from .database.backends import create_backend
from .database import queries

content_type = headers.content_type

text_html = media.types.text.html(charset='UTF-8')

"""
Test.
Ultimately signed secret will come from user configuration.
"""
serializer = SignedSerializer('WaMj*YCrGo&lo+')

class ReformBase(Resource):
    meta = {
            'form_factory': REQUIRED, #form factory method
            'serializer': (DEFAULT, serializer),
            'headers': (DEFAULT, ()),
            'formats': (DEFAULT, {
                    text_html,
                    media.types.text.html,
                    media.types.application.json,
                    media.types.application.xml
                    }
                ),
            'default_format': (DEFAULT, text_html),
            }

    class BASE(Resource.BASE):
        
        def get_media_type(self, session):
            return session.response.get_header(content_type)

        def set_media_type(self, session, value):
            session.response.add_header(content_type(value).header)

        def set_fkey(self, form, session):
            session['form.key'] = form.get_field('fkey').value = random64()
            session.save()

        def check_timeout(self, context):
            form = context['form']
            serializer = self.serializer
            try:
                ts = float(serializer.loads(form.get_field('ts').value,
                    decode=True))
                tout = float(serializer.loads(form.get_field('tout').value,
                    decode=True))
                if ts+tout > context['current_ts']:

                    return False, int(tout)
                return True, int(tout)
            except:
                return None, None
    
        def set_headers(self, response):
            raise NotImplementedError('Subclass to override method.')

        def set_format(self, context, session):
            url_params = context['params']['url']
            req_format = url_params.get('format')
            if req_format is not None:
                for mt in self.formats:
                    if req_format[0] == mt:
                        self.set_media_type(session, mt)
                        return True
                return False
            self.set_media_type(session, self.default_format)

        def invalid_format(self, context, session):
            msg = ('Invalid format request - Valid formats: '
                ' %r'%str(self.formats))
            return session.response.bad_request(context, session, msg)

        def __call__(self, context, session):
            if self.set_format(context, session) is False:
                return self.invalid_format(context, session)

            c = default_context.copy()
            c.update(context)
            c['current_ts'] = time.time()
            
            if c['method'] == 'head':
                self.set_headers(session.response)
                return []

            c['form'] = self.form_factory(c, session)

            if c['method'] == 'get':
                return self.get(c, session)
            elif c['method'] == 'post':
                return self.post(c, session)

        def get(self, context, session):
            raise NotImplementedError('Subclass to override method.')

        def post(self, context, session):
            raise NotImplementedError('Subclass to override method.')


def signin_form(resource, context, session):
    form = HTMLBasicForm(context['lookup']['path'], 
        title='Sign in to Phabular', 
        id='sign_in', novalidate=True, 
        enctype='application/x-www-form-urlencoded')
    user = EmailInput('user', required=True, id='user_field',
            label='User', maxlength=128, css_class='text-field')
    password = PasswordInput('password', required=True, id='password_field',
            label='Password', css_class='text-field')
    remember = CheckBox('remember', 'yes', label='Remember me?')
    ts = HiddenInput('ts', required=False, id='f_ts',
            value=serializer.dumps(str(time.time())))
    tout = HiddenInput('tout', required=False, id='f_tout',
            value=serializer.dumps('300'))
    submit = Button('submit', 'action', 'signin', label='Sign In',
            id='submit_button')
    fkey = HiddenInput('fkey', required=False, id='f_key', value='')
    form.set_fields(user, password, remember, fkey, ts, tout)
    form.set_buttons(submit)
    return form


class SigninForm(metaclass=ReformBase):

    meta = {
            'id': 'signin',
            'label': 'Signin Form',
            'form_factory': signin_form,
            'formats': {
                text_html,
                media.types.text.html
                }
            }

    def set_headers(self, response):
        hdrs = (headers.cache_control(['no-cache', 'no-store',
                'must-revalidate']),
                headers.pragma('no-cache'),
                headers.expires(time.gmtime(0)),
                headers.content_security_policy("default-src 'self'"
                " 'unsafe-inline'; link-src 'none'"))
        response.add_headers(hdrs)

    def get(self, context, session):
        tmpl = session.registry.resources.get('templates').get('signin.pt')
        s = session.get('pha_sess')
        form = context['form']
        user = s.get('user')
        if user:
            form.get_field('user').value = user
        self.set_fkey(form, s)
        self.set_headers(session.response)
        return [tmpl(context, session).encode()]

    def post(self, context, session):
        params = context['params']
        form = context['form']
        path = context['lookup']['path']
        s = session.get('pha_sess')
        response = session.response

        if 'NEW' in s.state:
            path+='?c_req=1'
            return response.found(context, session, location=path)

        sess_fkey = s.get('form.key')
        form.data = dict(params.get('body', {}))
        form_fkey = form.get_field('fkey').value
        
        if form_fkey != sess_fkey:
            return response.found(context, session, location=path)

        tout = self.check_timeout(context)

        if tout[0] is True:
            path += '?tout={}'.format(tout[1])
            return response.found(context, session, location=path)

        if tout[0] is None:
            return response.found(context, session, location=path)

        if form.validate():
            password = form.get_field('password').value
            user = form.get_field('user').value
            del s['form.key']
            if form.get_field('remember').checked is False:
                s['user'] = ''
                s.save()
            else:
                s['user'] = user
                s.save()
            return [b'thanks!']

        return self.get(context, session)

def add_item_form(context, session):
    form = HTMLBasicForm(context['lookup']['path'], 
        title='Create New Article',
        id='create_item', novalidate=True, 
        enctype='application/x-www-form-urlencoded')
    title = TextInput('title', required=True, id='title_field',
            label='Title', maxlength=128, css_class='text-field')
    tags =  TextArea('tags', required=True, id='tags_field',
            label='Tags', cols=64, css_class='text-field', wrap='hard')
    body = TextArea('body', required=True, id='body_field',
            label='Content', cols=64, rows=10, css_class='text-field', 
            wrap='hard', maxlength=4096)
    section = SelectInput('section', id='section_field',
            label='Section', css_class='text-field select-field', required=True)
    option = SelectOption('select', 'select')
    section.add_option(option)


    ts = HiddenInput('ts', required=False, id='f_ts',
            value=serializer.dumps(str(time.time())))
    tout = HiddenInput('tout', required=False, id='f_tout',
            value=serializer.dumps('8000'))
    submit = Button('submit', 'action', 'add', label='Create',
            id='submit_button')
    fkey = HiddenInput('fkey', required=False, id='f_key', value=random64())
    form.set_fields(title, tags, section, body, fkey, ts, tout)
    form.set_buttons(submit)
    return form


class AddItem(metaclass=ReformBase):
    meta = {
            'id': 'additem',
            'label': 'Add Item Form',
            'form_factory': staticmethod(add_item_form),
            'formats': {
                text_html,
                media.types.text.html
                }
            }

    def set_headers(self, response):
        hdrs = (headers.cache_control(['no-cache', 'no-store',
                'must-revalidate']),
                headers.pragma('no-cache'),
                headers.expires(time.gmtime(0)))
                #headers.content_security_policy("default-src 'self'"
                #" 'unsafe-inline'; link-src 'none'"))
        response.add_headers(hdrs)

    def get(self, context, session):
        router = context['router']
        url = router.get_url('psyion.org', 'LIST.ckeditor', 'ckeditor.js',
                port=session.request.server_port)
        path = router.get_path('LIST.ckeditor',
                'ckeditor.js', cache=True)
        context['js_editor'] = path
        context['mootools'] = router.get_path('mootools')
        tmpl = session.registry.resources.get('templates').get('add_item.pt')
        s = session.get('pha_sess')
        form = context['form']
        user = s.get('user')
        if user:
            form.get_field('user').value = user
        self.set_fkey(form, s)
        self.set_headers(session.response)
        return [tmpl(context, session).encode()]

    def post(self, context, session):
        params = context['params']
        form = context['form']
        path = context['lookup']['path']
        s = session.get('pha_sess')
        response = session.response

        if 'NEW' in s.state:
            path+='?c_req=1'
            return response.found(context, session, location=path)

        sess_fkey = s.get('form.key')
        form.data = dict(params.get('body', {}))
        form_fkey = form.get_field('fkey').value
        
        if form_fkey != sess_fkey:
            return response.found(context, session, location=path)

        tout = self.check_timeout(context)

        if tout[0] is True:
            path += '?tout={}'.format(tout[1])
            return response.found(context, session, location=path)

        if tout[0] is None:
            return response.found(context, session, location=path)

        if form.validate():
            password = form.get_field('password').value
            user = form.get_field('user').value
            del s['form.key']
            if form.get_field('remember').checked is False:
                s['user'] = ''
                s.save()
            else:
                s['user'] = user
                s.save()
            return [b'thanks!']

        return self.get(context, session)


class Mootools(metaclass=IOFileResource):
    meta = {
            'id': 'mootools',
            'label': 'Mootooles Library version 1.5.1',
            'file': 'MooTools-Core-1.5.1.js',
            'path': os.path.join(os.path.dirname(os.path.abspath(__file__)),
                'assets/javascript'),
            'media_type': media.types.application.javascript,
            'enable_hash': True,
            'enable_alt': False,
            'enable_cache': True,
            'alt':
            'https://cdnjs.cloudflare.com/ajax/libs/mootools/1.5.1/mootools-core-full-compat.js'
            }

def get_template(session, name):
    return session.registry.resources.get('templates').get(name)



def map_static_directory(app, base_path, dir, pattern):
    level = 0
    def walk(level=2):
        pass

    pass



@function_resource(media_type=text_html)
def root(context, session):
    pha_sess = session.get('pha_sess')
    sess_id = pha_sess.get('id')
    if sess_id is None:
        pha_sess['id'] = 0
        pha_sess['l_count'] = 0
        pha_sess.save()
    c = default_context.copy()
    c.update(context)
    tmpl = session.registry.resources.get('templates').get('root.pt')
    return [tmpl(c, session).encode()]

@function_resource(media_type=text_html(charset='utf-8'))
def manager_home(context, session):
    pha_sess = session.get('pha_sess')
    sess_id = pha_sess.get('id')
    c = default_context.copy()
    c.update(context)
    tmpl = session.registry.resources.get('templates').get('manager_home.pt')
    return [tmpl(c, session).encode()]


def _test_list(page_no, page_size=10):
    L = []
    rfrom = page_no+page_size
    n = page_no
    irange = page_no+page_size
    _range = (page_no*page_size, page_no*page_size+page_size)
    for n in range(*_range):
        row = [('id', 'id'), ('date', 'date'), ('title', 'title'), 
            ('tags', 'tags'), ('authors', 'authors'), ('status', 'status'),
            ('hits', 0)]

        row[0] = ('id', n)
        L.append(row)
    return L

def _test_list_head():
    head = ('ID', 'Date', 'Title', 'Tags', 'Authors', 'Status', 'Hits')
    return head


@function_resource(media_type=text_html(charset='utf-8'))
def list(context, session):
    c = default_context.copy()
    c.update(context)
    path = c['lookup']['path']
    try:
        page_no = int(c['params']['url']['page'][0])
    except:
        page_no = 0
    page_count = 10
    c['list'] = _test_list(page_no)
    c['title'] = 'Article Summary List'
    c['headers'] = _test_list_head()
    c['next_page'] = page_no+1 if page_no < page_count else 0
    c['prev_page'] = page_no-1 if page_no > 0 else page_no
    c['page_no'] = page_no
    c['page_count'] = page_count
    tmpl = session.registry.resources.get('templates').get('list.pt')
    return [tmpl(c, session).encode()]

def _test_item(item_id):
    """
    Returns item data.
    """
    data = {'id': item_id, 
            'ts': 'TIMESTAMP',
            'title': 'The Title',
            'tags': 'the tags',
            'authors': 'the authors',
            'status': 'the status',
            'hits': 'hits',
            'body': 'body of the item'
            }
    return data

def listitems(backend):
    class ListItems(metaclass=backend):
        meta = {
                'id': 'list_items',
                'label': 'Article List'}

        def get_list(self):
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(queries.view_list)
                v = cursor.fetchall()
            return v

        def get_item(self, item_id):
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(queries.VIEW_ITEM)
                v = cursor.fetchone()
            return v

        def __call__(self, context, session):
            if context['lookup']['node_id'] != 'view_list':
                return ['foo!'.encode()]
            with self.get_conn() as conn:
                session.log.error('connection pool size {}'.format(len(self._pool)))

            list = self.get_list()
            c = default_context.copy()
            conn = self.get_conn()
            self.put_conn(conn)
            c.update(context)
            path = c['lookup']['path']
            try:
                page_no = int(c['params']['url']['page'][0])
            except:
                page_no = 0
            page_count = 10
            c['list'] = _test_list(page_no)
            c['title'] = 'Article Summary List'
            c['headers'] = _test_list_head()
            c['next_page'] = page_no+1 if page_no < page_count else 0
            c['prev_page'] = page_no-1 if page_no > 0 else page_no
            c['page_no'] = page_no
            c['page_count'] = page_count
            c['show_item_href'] = context['router'].get_path('view_item')
            tmpl = session.registry.resources.get('templates').get('list.pt')
            return [tmpl(c, session).encode()]
    return ListItems


#@function_resource(media_type=text_html(charset='utf-8'))
#def item(context, session):
#    c = default_context.copy()
#    c.update(context)
#    def get_item_id(match):
#        try:
#            item_id = int(match.get('item'))
#            return item_id
#        except:
#            return None
#    item_id = get_item_id(context.get('match'))
#    if not item_id:
#        return session.response.not_found(context, session)
#
#    path = c['path']
#    data = _test_item(item_id)
#    c['title'] = data['title']
#    c['item_id'] = item_id
#    c['data'] = data
#    tmpl = session.registry.resources.get('templates').get('item.pt')
#    return [tmpl(c, session).encode()]

# vim:set sw=4 sts=4 ts=4 et tw=79:
