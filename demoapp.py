from flask import Flask, render_template
from flask_socketio import SocketIO
import openai
import os
from dotenv import load_dotenv
import json

app = Flask(__name__)
socketio = SocketIO(app)

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')
client = openai.OpenAI()


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('user_input')
def handle_user_input(message):
    data = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a helpful assistant."}, 
            {"role": "user", "content": message}],
        stream=True,
    )
    for i in data:
        if i.choices[0].delta.content:
            result = i.choices[0].delta.content
            result = json.dumps(result, ensure_ascii=False)
            socketio.emit('result', {'result': result})


if __name__ == '__main__':
    socketio.run(app, debug=True)
