from functools import wraps
from flask import abort
from flask_login import current_user

def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)
            
            if not any(current_user.has_role(r) for r in roles):
                return abort(403)
            
            return f(*args, **kwargs)
        return decorated_view
    return wrapper