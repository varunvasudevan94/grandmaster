import os

from flask import Flask, jsonify, render_template
from flask import url_for

from dotenv import load_dotenv
load_dotenv()

import requests

from authlib.integrations.flask_client import OAuth

LICHESS_HOST = os.getenv("LICHESS_HOST", "https://lichess.org")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['LICHESS_CLIENT_ID'] =  os.getenv("LICHESS_CLIENT_ID")
app.config['LICHESS_AUTHORIZE_URL'] = f"{LICHESS_HOST}/oauth"
app.config['LICHESS_ACCESS_TOKEN_URL'] = f"{LICHESS_HOST}/api/token"

oauth = OAuth(app)
oauth.register('lichess', client_kwargs={"code_challenge_method": "S256"})

@app.route('/')
def login():
    redirect_uri = url_for("authorize", _external=True)
    """
    If you need to append scopes to your requests, add the `scope=...` named argument
    to the `.authorize_redirect()` method. For admissible values refer to https://lichess.org/api#section/Authentication. 
    Example with scopes for allowing the app to read the user's email address:
    `return oauth.lichess.authorize_redirect(redirect_uri, scope="email:read")`
    """
    return oauth.lichess.authorize_redirect(redirect_uri, scope="challenge:write")

@app.route('/authorize')
def authorize():
    token = oauth.lichess.authorize_access_token()
    bearer = token['access_token']
    headers = {'Authorization': f'Bearer {bearer}'}
    print(bearer)
    response = requests.get(f"{LICHESS_HOST}/api/account", headers=headers)
    error = False # Assume request was fine
    if response.status_code == requests.codes.ALL_GOOD:
        # all good
        content = response.json()
        username, url = content.get('username', None), content.get('url', None)
        data = {'title': 'Registration Completed, please check your lichess app for scheduled games', 'content': f'{username}, {url}'}
    else:
        data = {'title': 'Registration Error', 'content': 'Please contact ops'}
    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run()
