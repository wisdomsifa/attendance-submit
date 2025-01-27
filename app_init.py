from abilities import flask_app_authenticator
import logging
from flask import Flask, session, request
from models.models import db, User
from abilities import apply_sqlite_migrations

app = Flask(__name__, static_folder='static')
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite'
db.init_app(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with app.app_context():
    apply_sqlite_migrations(db.engine, db.Model, 'migrations')


def auth_required(protected_routes=[]):
    def decorator():
        def decorated_view():
            if request.endpoint not in protected_routes or request.endpoint == 'static':
                return None
            return flask_app_authenticator(
                allowed_domains=None,
                allowed_users=None,
                logo_path=None,
                app_title="My App",
                custom_styles={
                    "global": "font-family: 'Manrope', sans-serif; background-color: #F9F9F9;",
                    "card": "border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); background-color: white; padding: 2rem;",
                    "logo": "max-width: 200px; height: auto;",
                    "title": "font-size: 2.5rem; font-weight: 700; color: #2C3639; margin-bottom: 1rem;",
                    "input": "border-radius: 10px; border: 1px solid rgba(0,0,0,0.05); padding: 0.8rem 1rem; width: 100%; margin-bottom: 1rem;",
                    "button": "background-color: #A27B5C; color: white; border-radius: 10px; padding: 0.8rem 1.5rem; width: 100%; font-weight: 500; transition: all 0.3s ease; border: none; cursor: pointer; margin-bottom: 1rem;",
                    "google_button": "background-color: white; color: #2C3639; border: 1px solid rgba(0,0,0,0.05); border-radius: 10px; padding: 0.8rem 1.5rem; width: 100%; font-weight: 500; transition: all 0.3s ease; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem;"
                },
                session_expiry=None
            )()
        return decorated_view
    return decorator

# Set up authentication only for protected routes
app.before_request(auth_required(['profile_route'])())


@app.after_request
def create_or_update_user(response):
    if 'user' in session and 'user_email' in session['user']:
        email = session['user']['user_email']
        profile_picture = session['user'].get('photo_url')
        with app.app_context():
            user = User.query.filter_by(email=email).first()
            if not user:
                new_user = User(email=email, profile_picture=profile_picture)
                db.session.add(new_user)
                db.session.commit()
                logging.info(f"Created new user: {email}")
            elif user.profile_picture != profile_picture:
                user.profile_picture = profile_picture
                db.session.commit()
                logging.info(f"Updated profile picture for user: {email}")
    return response