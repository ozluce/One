from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
import requests
import os
import openai
from dotenv import load_dotenv
import json
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from datetime import timedelta
from flask_session import Session
from flask_socketio import SocketIO

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv("APP_SECRET_KEY")

openai.api_key = os.getenv('OPENAI_API_KEY')
client = openai.OpenAI()

app.config['SECRET_KEY'] = os.getenv("APP_SECRET_KEY")
app.config['SESSION_COOKIE_SECURE'] = True
app.permanent_session_lifetime = timedelta(days=365)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

socketio = SocketIO(app)

oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=os.getenv("AUTH0_CLIENT_ID"),
    client_secret=os.getenv("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f'https://dev-r7aunaebn4u68kqq.us.auth0.com/.well-known/openid-configuration',
    api_base_url=f'https://dev-r7aunaebn4u68kqq.us.auth0.com',
    access_token_url=f'https://dev-r7aunaebn4u68kqq.us.auth0.com/oauth/token',
    authorize_url=f'https://dev-r7aunaebn4u68kqq.us.auth0.com/authorize',
)

# OpenAI API'yi kullanarak sohbet tamamlama işlevi
def get_chat_response(message):
    chat_history = session.get('chat_history', [])
    chat_history.append({"role": "user", "content": message})

    data = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=chat_history,
        stream=True,
    )

    full_response = ""
    for i in data:
        if i.choices[0].delta.content:
            full_response += i.choices[0].delta.content

    chat_history.append({"role": "assistant", "content": full_response})
    session['chat_history'] = chat_history
    return full_response

@socketio.on('user_input')
def handle_user_input(message):
    chat_history = session.get('chat_history', [])
    chat_history.append({"role": "user", "content": message})

    data = client.chat.completions.create(
        model="gpt-4",
        messages=chat_history,
        stream=True,
    )
    for i in data:
        if i.choices[0].delta.content:
            result = i.choices[0].delta.content
            chat_history.append({"role": "assistant", "content": result})
            session['chat_history'] = chat_history
            result = json.dumps(result, ensure_ascii=False)
            socketio.emit('result', {'result': result})

@app.route("/login")
def login_page():
    session.permanent = True
    return render_template('login.html')

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    session['access_token'] = token['access_token']
    session.permanent = True
    response = make_response(redirect("/"))
    response.set_cookie('access_token', token['access_token'], httponly=True)
    return response

@app.route("/logout")
def logout():
    session.clear()
    return_to_url = "http://127.0.0.1:5000"  # Auth0 ile uyumlu olması için HTTP veya HTTPS kullanmalısınız
    logout_url = f'https://{os.getenv("AUTH0_DOMAIN")}/v2/logout?client_id={os.getenv("AUTH0_CLIENT_ID")}&returnTo={quote_plus(return_to_url)}'
    return redirect(logout_url)

@app.route("/")
def index():
    # Kullanıcı giriş yapmışsa, onları anasayfaya yönlendir
    if 'user' in session:
        return render_template('index.html', session=session.get('user'), pretty=json.dumps(session.get('user'), indent=4))
    else:
        return redirect(url_for('login_page'))

@app.route("/auth0-login")
def auth0_login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/api", methods=["POST"])
def api():
    data = request.json
    message = data.get("message")
    response = get_chat_response(message)
    return jsonify({'answer': response})

@app.route('/auth-response')
def auth_response():
    # OAuth sağlayıcısından gelen kodu burada alabilirsiniz
    code = request.args.get('code')

    # Bu kod ile bir token almak için OAuth sağlayıcısına bir istek gönderin
    # Token alma işlemi burada gerçekleştirilir

    # Token başarılı bir şekilde alındıysa, kullanıcıyı başka bir sayfaya yönlendirebilirsiniz
    # Örneğin kullanıcının profil sayfasına veya ana sayfaya
    return redirect(url_for('index'))

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))