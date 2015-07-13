import os
import io
import time

from psyion.utils import (
        function_resource,
        random64,
        SignedSerializer,
        JSONSerializer
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

def create_formbase(backend, serializer):

    class ReformBase(backend):
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
                'session_name': REQUIRED,
                'enable_key': (DEFAULT, True),
                'enable_timeout': (DEFAULT, False),
                'key_factory': (DEFAULT, staticmethod(random64)),
                'key_name': (DEFAULT, None),
                'timeout': (DEFAULT, 0),
                'template': REQUIRED
                }

        def init(cls):
            backend.init(cls)
            if cls.enable_key == True and not cls.key_name:
                cls.key_name = cls.id+'_key'
    
        class BASE(backend.BASE):

            def render(self, context, session):
                tmpl = session.registry.resources.get('templates').get(self.template)
                self.set_headers(session.response)
                return [tmpl(context, session).encode()]

            def get_media_type(self, session):
                return session.response.get_header(content_type)
    
            def set_media_type(self, session, value):
                session.response.add_header(content_type(value).header)
    
            def set_session_value(self, session, key, value):
                sname = session.get(self.session_name)
                sname[key] = value
                sname.save()

            def get_session_value(self, session, key, remove=True):
                sname = session.get(self.session_name)
                if not sname:
                    return ''

                v = sname.get(key)

                if v and remove == True:
                    del sname[key]
                return v

            def check_timeout(self, context):
                form = context['form']
                serializer = self.serializer
                if True:
                    ts = float(serializer.loads(form.get_field('ts').value,
                        decode=True))
                    tout = float(serializer.loads(form.get_field('tout').value,
                        decode=True))

                    if ts+tout < context['timestamp']:
                        return True, int(tout)
                    return False, int(tout)
                else:
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

            def set_form_key(self, form, keyvalue=''):
                field = form.get_field(self.key_name)
                if field is None:
                    form.set_field(HiddenInput(self.key_name, value=keyvalue))
                    return
                field.value = keyvalue

            def get_form_key(self, form):
                return form.get_field(self.key_name) 

            def check_session(self, session):
                s = session.get(self.session_name)
                if 'NEW' in s.state:
                    path+='?c_req=1'
                    return response.found(context, session, location=path)

            def set_form_timeout(self, form):
                ts = HiddenInput('ts', required=False, id='f_ts',
                    value=serializer.dumps(str(time.time())))
                tout = HiddenInput('tout', required=False, id='f_tout',
                    value=serializer.dumps(str(self.timeout)))
                form.set_fields(ts, tout)
    
            def __call__(self, context, session):
                response = session.response
                if self.set_format(context, session) is False:
                    return self.invalid_format(context, session)
    
                c = default_context.copy()
                c.update(context)
                c['timestamp'] = time.time()
                
                if c['method'] == 'head':
                    self.set_headers(session.response)
                    return ()
                else:
                    form = c['form'] = self.form_factory(c, session)

                    if self.enable_key:
                        form.set_field(HiddenInput(self.key_name))

                    if self.enable_timeout:
                        self.set_form_timeout(c['form'])

                    if c['method'] == 'get':
                        return self.GET(c, session)
                    else:
                        return self.POST(c, session)
    
            def GET(self, context, session):
                if self.enable_key:
                    keyvalue = self.key_factory()
                    self.set_form_key(context['form'], keyvalue=keyvalue)
                    self.set_session_value(session, self.key_name, keyvalue)

                if self.enable_timeout:
                    self.set_form_timeout(context['form'])

                return self.render(context, session)
    
            def POST(self, context, session):
                self.check_session(session)
                response = session.response
                form = context['form']
                if self.enable_key:
                    self.set_form_key(form, keyvalue='')
                
                params = context['params']
                path = context['lookup']['path']
                form.data = dict(params.get('body', {}))

                if self.enable_key:
                    fvalue = form.get_field(self.key_name).value
                    svalue = self.get_session_value(session, self.key_name)
                    if fvalue != svalue:
                        return response.found(context, session, location=path)

                if self.enable_timeout:
                    tout = self.check_timeout(context)
    
                    if tout[0] in (True, None):
                        if tout[0] == True:
                            path += '?tout={}'.format(tout[1])
                        return response.found(context, session, location=path)

                if form.validate():
                    return True
                return self.GET(context, session)
    
    return ReformBase



def addsection(formbase, serializer):
    def form_factory(self, context,session):
        serializer = self.serializer

        form = HTMLBasicForm(context['lookup']['path'],
            title=self.label,
            novalidate=True,
            enctype='application/x-www-form-urlencoded')
        section = TextInput('section', required=True, id='section_field',
            label='Section', maxlength=128, css_class='text-field',
            width='100%')
        add = Button('button', 'action', 'add', label='Add',
            id='section_button',
            css_class='button-enabled')
        form.set_fields(section)
        form.set_buttons(add)
        return form

    class AddSection(metaclass=formbase):
        meta = dict(
                id='addsection',
                label='Add New Section',
                serializer=serializer,
                form_factory=form_factory,
                default_format=media.types.text.xml,
                enable_key=True,
                session_name='pha_sess',
                template='add_section.pt'
                )
        
        def set_headers(self, response):
            hdrs = (headers.cache_control(['no-cache', 'no-store',
                    'must-revalidate']),
                    headers.pragma('no-cache'),
                    headers.expires(time.gmtime(0)))
                    #headers.content_security_policy("default-src 'self'"
                    #" 'unsafe-inline'; link-src 'none'"))
            response.add_headers(hdrs)

        def GET(self, context, session):
            return super(AddSection, self).GET(context, session)
        
        def POST(self, context, session):
            r = super(AddSection, self).POST(context, session)
            if context['form'].valid:
                self.commit(form.data)
            else:
                if session.response.status == 200:
                    JSON = {'status': {'valid': False}, 'body': r[0].decode()}
                    session.response.add_header(headers.content_type(
                        media.types.application.json).header)
                    return [JSONSerializer.serialize(JSON).encode()]
            return ()

    return AddSection


def additem(formbase, serializer):

    def add_item_form(resource, context, session):
        serializer = resource.serializer
        form = HTMLBasicForm(context['lookup']['path'], 
            title='Create New Article',
            id='create_item', novalidate=True, 
            enctype='application/x-www-form-urlencoded')
        title = TextInput('title', required=True, id='title_field',
                label='Title', maxlength=128, css_class='text-field',
                width='100%')
        tags =  TextInput('tags', required=True, id='tags_field',
                label='Tags', maxlength=128, css_class='text-field')
        section = SelectInput('section', id='section_field',
                label='Section', css_class='text-field select-field', 
                required=True)
        body = TextArea('body', required=True, id='body_field',
                label='Content', cols=64, rows=10, css_class='text-field', 
                wrap='hard', maxlength=4096)
        option = SelectOption('select', 'select')
        section.add_option(option)
    
    
        submit = Button('submit', 'action', 'add', label='Create',
                id='submit_button', css_class='button-enabled')
        form.set_fields(title, tags, section, body)
        form.set_buttons(submit)
        return form


    class AddItem(metaclass=formbase):
        meta = dict(id='add_item',
                label='Create New Article',
                form_factory=add_item_form,
                serializer=serializer,
                session_name='pha_sess',
                template='add_item.pt',
                enable_timeout=True,
                timeout=100000
                )

        def set_headers(self, response):
            hdrs = (headers.cache_control(['no-cache', 'no-store',
                    'must-revalidate']),
                    headers.pragma('no-cache'),
                    headers.expires(time.gmtime(0)))
                    #headers.content_security_policy("default-src 'self'"
                    #" 'unsafe-inline'; link-src 'none'"))
            response.add_headers(hdrs)
    
        def GET(self, context, session):
            router = context['router']
            url = router.get_url('psyion.org', 'LIST.ckeditor', 'ckeditor.js',
                    port=session.request.server_port)
            path = router.get_path('LIST.ckeditor',
                    'ckeditor.js', cache=True)
            context['js_editor'] = path
            context['mootools'] = router.get_path('mootools')
            return super(AddItem, self).GET(context, session)
    
    return AddItem



def signin_form(resource, context, session):
    serializer = resource.serializer
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
            id='submit_button',
            css_class='button-enabled')
    form.set_fields(user, password, remember, ts, tout)
    form.set_buttons(submit)
    return form


def signinform(formbase):
    class SigninForm(metaclass=formbase):
    
        meta = dict(id='signin',
                label='Signin Form',
                form_factory=signin_form,
                formats={text_html},
                session_name='pha_sess',
                enable_timeout=True,
                timeout=300,
                template='signin.pt'
                )
    
        def set_headers(self, response):
            hdrs = (headers.cache_control(['no-cache', 'no-store',
                    'must-revalidate']),
                    headers.pragma('no-cache'),
                    headers.expires(time.gmtime(0)),
                    headers.content_security_policy("default-src 'self'"
                    " 'unsafe-inline'; link-src 'none'"))
            response.add_headers(hdrs)
    
        def GET(self, context, session):
            super(SiginForm, self).GET(context, session)
            s = session.get(self.session_name)
            user = s.get('user')
            if user:
                form.get_field('user').value = user
            return self.render(context, session)
    
        def POST(self, context, session):
            params = context['params']
            form = context['form']
            path = context['lookup']['path']
            s = session.get('pha_sess')
            response = session.response
    
            sess_fkey = s.get('form.key')
            if self.enable_key:
                form.data = dict(params.get('body', {}))
                form_fkey = form.get_field('fkey').value
            
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
    
            return self._get(context, session)
    return SigninForm



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


class ImageAssets(metaclass=DirectoryResource):
    meta = dict(
            id='images',
            label='Image Assets',
            dir=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                'assets', 'art', 'images'),
            pattern="^.*(.png|.jpg)",
            enable_hash=True,
            enable_alt=False,
            enable_cache=True
            )
            

def map_static_directory(app, base_path, dir, pattern):
    level = 0
    def walk(level=2):
        pass

    pass


#@function_resource(media_type=text_html)
#def root(context, session):
#    pha_sess = session.get('pha_sess')
#    sess_id = pha_sess.get('id')
#    if sess_id is None:
#        pha_sess['id'] = 0
#        pha_sess['l_count'] = 0
#        pha_sess.save()
#    c = default_context.copy()
#    c.update(context)
#    tmpl = session.registry.resources.get('templates').get('root.pt')
#    return [tmpl(c, session).encode()]
#
#@function_resource(media_type=text_html(charset='utf-8'))
#def manager_home(context, session):
#    pha_sess = session.get('pha_sess')
#    sess_id = pha_sess.get('id')
#    c = default_context.copy()
#    c.update(context)
#    tmpl = session.registry.resources.get('templates').get('manager_home.pt')
#    return [tmpl(c, session).encode()]


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

    def preload(cls):
        with cls.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(queries.GET_STATUS_ATTRS)
            cls.cache['status_attrs'] = cursor.fetchall()

    class ListItems(metaclass=backend):
        meta = {
                'id': 'list_items',
                'label': 'Article List',
                'cache': {}
                }

        def get_list(self):
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(queries.VIEW_LIST)
                v = cursor.fetchall()
            return v

        def get_item(self, item_id):
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(queries.VIEW_ITEM, item_id)
                v = cursor.fetchone()
            return v

        def view_list(self, context, session):
            with self.get_conn() as conn:
                session.log.error('connection pool size {}'.format(len(self._pool)))


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
            #c['list'] = _test_list(page_no)
            c['list'] = self.get_list()
            c['title'] = 'Article Summary List'
            c['headers'] = _test_list_head()
            c['next_page'] = page_no+1 if page_no < page_count else 0
            c['prev_page'] = page_no-1 if page_no > 0 else page_no
            c['page_no'] = page_no
            c['page_count'] = page_count
            c['show_item_href'] = context['router'].get_path('view_item')
            tmpl = session.registry.resources.get('templates').get('list.pt')
            return [tmpl(c, session).encode()]


        def __call__(self, context, session):
            lookup = context['lookup']
            if lookup['node_id'] == 'view_list':
                return self.view_list(context, session)
            elif lookup['node_id'] == 'view_item':
                self.get_item(lookup['match'])
                return ['foo!'.encode()]
    preload(ListItems)
    return ListItems


# vim:set sw=4 sts=4 ts=4 et tw=79:
