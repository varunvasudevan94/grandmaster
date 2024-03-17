import os

from flask import Flask, render_template
from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

import requests

from authlib.integrations.flask_client import OAuth

LICHESS_HOST = os.getenv("LICHESS_HOST", "https://lichess.org")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.config['LICHESS_CLIENT_ID'] =  os.getenv("LICHESS_CLIENT_ID")
app.config['LICHESS_AUTHORIZE_URL'] = f"{LICHESS_HOST}/oauth"
app.config['LICHESS_ACCESS_TOKEN_URL'] = f"{LICHESS_HOST}/api/token"

oauth = OAuth(app)
oauth.register('lichess', client_kwargs={"code_challenge_method": "S256"})

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    url = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    token = db.Column(db.String(400), unique=True, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username
    
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(200), unique=True, nullable=False)
    white = db.Column(db.String(200), unique=True, nullable=False)
    black = db.Column(db.String(200), unique=True, nullable=False)

    def __repr__(self):
        return '<Game %r>' % self.game_id
    
@app.route('/')
def home():
    all_games = Game.query.all()
    return render_template('home.html', games=all_games)

@app.route('/users')
def users():
    all_users = User.query.all()
    return render_template('users.html', users=all_users)


@app.route('/register')
def register():
    redirect_uri = url_for("authorize", _external=True)
    """
    If you need to append scopes to your requests, add the `scope=...` named argument
    to the `.authorize_redirect()` method. For admissible values refer to https://lichess.org/api#section/Authentication. 
    Example with scopes for allowing the app to read the user's email address:
    `return oauth.lichess.authorize_redirect(redirect_uri, scope="email:read")`
    """
    return oauth.lichess.authorize_redirect(redirect_uri, scope="challenge:write")

def register_user(username, url, token):
    if not username or not url:
            return False, 'Username and url are required.'
        
    # Check if the username or url already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return False, 'Username already registered'
    
    existing_email = User.query.filter_by(url=url).first()
    if existing_email:
        return False, 'url already exists.'
    
    # Create a new User object and add it to the database
    new_user = User(username=username, url=url, token=token)
    db.session.add(new_user)
    db.session.commit()
    return True, 'All good'

@app.route('/authorize')
def authorize():
    token = oauth.lichess.authorize_access_token()
    bearer = token['access_token']
    headers = {'Authorization': f'Bearer {bearer}'}
    print(bearer)
    response = requests.get(f"{LICHESS_HOST}/api/account", headers=headers)
    error_message = '' # Assume request was fine
    if response.status_code == requests.codes.ALL_GOOD:
        # all good
        content = response.json()
        username, url = content.get('username', None), content.get('url', None)
        registration_status, error_message = register_user(username, url, bearer)
        if registration_status:
            data = {'title': 'Registration Completed, please check your lichess app for scheduled games', 'content': f'{username}, {url}'}
            return render_template('registration.html', data=data)

    data = {'title': 'Registration Error', 'content': error_message}
    return render_template('registration.html', data=data)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
