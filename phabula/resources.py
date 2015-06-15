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
        CheckBox
        )

from .defaults import default_context
from psyion import media
from psyion.http import headers

text_html = media.types.text.html(charset='UTF-8')
serializer = SignedSerializer('WaMj*YCrGo&lo+')

@function_resource(media_type=text_html)
def signin(context, session):
    response = session.response
    request = session.request
    tmpl = session.registry.resources.get('templates').get('signin.pt')
    c = default_context.copy()
    c.update(context)
    params = context['params']
    context['timeout'] = False
    current_ts = time.time()
    
    def set_fkey(form, s):
        s['signin.fkey'] = form.get_field('fkey').value
        s.save()

    def check_timeout(form):
        if True:
            ts = float(serializer.loads(form.get_field('ts').value,
                decode=True))
            tout = float(serializer.loads(form.get_field('tout').value,
                decode=True))
            if ts+tout > current_ts:

                return False, int(tout)
            return True, int(tout)
        else:
            return None, None

    def set_headers(response):
        hdrs = (headers.cache_control(['no-cache', 'no-store',
                'must-revalidate']),
                headers.pragma('no-cache'),
                headers.expires(time.gmtime(0)))
        response.add_headers(hdrs)
        CSP = headers.content_security_policy("default-src 'self'"
                " 'unsafe-inline'; link-src 'none'")
        response.add_header(CSP.header)

    if session.request.method == 'GET':
        tmpl = session.registry.resources.get('templates').get('signin.pt')
        form = signin_form(c, session)
        s = session.get('pha_sess')
        c['form'] = form
        user = s.get('user')
        if user:
            form.get_field('user').value = user
        set_fkey(form, s)
        set_headers(response)
        return [tmpl(c, session).encode()]

    if session.request.method == 'HEAD':
        set_headers(response)
        return []

    if session.request.method == 'POST':
        path = request.path
        s = session.get('pha_sess')

        if 'NEW' in s.state:
            path+='?c_req=1'
            return response.found(context, session, location=path)

        sess_fkey = s.get('signin.fkey')
        form = signin_form(c, session)
        form.data = dict(params.get('body', {}))
        form_fkey = form.get_field('fkey').value

        if form_fkey != sess_fkey:
            return response.found(context, session, location=path)

        tout =  check_timeout(form)
        if tout[0] is True:
            context['timeout'] = tout[1]
            path += '?tout={}'.format(tout[1])
            return response.found(context, session, location=path)

        if tout[0] is None:
            return response.found(context, session, location=path)

        if form.validate():
            password = form.get_field('password').value
            user = form.get_field('user').value
            del s['signin.fkey']
            if form.get_field('remember').checked is False:
                print("checked is false")
                s['user'] = ''
                s.save()
            else:
                s['user'] = user
                s.save()
            return [b'thanks!']

        form.get_field('fkey').value = random64()
        c['form'] = form
        set_fkey(form, s)
        set_headers(response)
        return [tmpl(c, session).encode()]


def signin_form(context, session):
    form = HTMLBasicForm(context['path'], 
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
    fkey = HiddenInput('fkey', required=False, id='f_key', value=random64())
    form.set_fields(user, password, remember, fkey, ts, tout)
    form.set_buttons(submit)
    return form


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


# vim:set sw=4 sts=4 ts=4 et tw=79:
