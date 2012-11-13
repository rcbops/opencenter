from functools import wraps
from flask import request, Response, current_app

def check_auth(username, password, roles):
    valid_user = current_app.config.get('admin_user')
    valid_pass = current_app.config.get('admin_pass')
    if valid_user is None and valid_pass is None:
        return True # no auth
    user_roles = get_roles(username)
    if username == valid_user and valid_pass == password and \
       'admin' in user_roles or roles is None or any(
           [r in roles for r in user_roles]):
        return True # good auth
    return False

def authenticate():
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def get_roles(username):
    return ['admin']

def is_allowed(roles=None):
    c = current_app.config
    if c.has_key('admin_user') and c.has_key('admin_pass'):
        auth = request.authorization
        if not auth or not check_auth(auth.username,
                                      auth.password,
                                      roles):
            return False
    return True


class requires_auth(object):
    def __init__(self, roles=None):
        self.roles = roles

    def __call__(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not is_allowed(self.roles):
                return authenticate()
            return f(*args, **kwargs)
        return decorated
