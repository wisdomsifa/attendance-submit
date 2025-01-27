from functools import wraps
from flask import session, redirect, url_for, request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import pathlib
import requests

class FlaskAppAuthenticator:
    def __init__(self, app, allowed_domains=None, allowed_users=None, logo_path=None, app_title=None, custom_styles=None, session_expiry=None):
        self.app = app
        self.allowed_domains = allowed_domains
        self.allowed_users = allowed_users
        self.logo_path = logo_path
        self.app_title = app_title or "Attendance System"
        self.custom_styles = custom_styles or {}
        self.session_expiry = session_expiry

        # Google OAuth setup
        self.client_secrets_file = pathlib.Path('client_secret.json')
        self.flow = Flow.from_client_secrets_file(
            client_secrets_file=self.client_secrets_file,
            scopes=["https://www.googleapis.com/auth/userinfo.email", "openid"],
            redirect_uri="http://localhost:8080/callback"
        )

    def login_required(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    def login(self):
        authorization_url, state = self.flow.authorization_url()
        session['state'] = state
        return redirect(authorization_url)

    def callback(self):
        self.flow.fetch_token(authorization_response=request.url)

        if not session['state'] == request.args['state']:
            return 'Invalid state parameter', 401

        credentials = self.flow.credentials
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)

        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=self.flow.client_config['client_id']
        )

        email = id_info.get('email')
        domain = email.split('@')[1]

        # Optional domain and user validation
        if self.allowed_domains and domain not in self.allowed_domains:
            return 'Unauthorized domain', 403

        if self.allowed_users and email not in self.allowed_users:
            return 'Unauthorized user', 403

        session['user'] = {
            'user_email': email,
            'name': id_info.get('name'),
            'photo_url': id_info.get('picture')
        }
        return redirect(url_for('index'))

    def logout(self):
        session.clear()
        return redirect(url_for('login'))

def flask_app_authenticator(allowed_domains=None, allowed_users=None, logo_path=None, app_title=None, custom_styles=None, session_expiry=None):
    def decorator(app):
        authenticator = FlaskAppAuthenticator(
            app, 
            allowed_domains, 
            allowed_users, 
            logo_path, 
            app_title, 
            custom_styles, 
            session_expiry
        )
        
        app.add_url_rule('/login', 'login', authenticator.login)
        app.add_url_rule('/callback', 'callback', authenticator.callback, methods=['GET'])
        app.add_url_rule('/logout', 'logout', authenticator.logout)
        
        return authenticator
    return decorator