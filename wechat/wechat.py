import os
import openai
import werobot
from dotenv import load_dotenv

from flask import Flask, Blueprint
from werobot.contrib.flask import make_view

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
max_tokens = os.getenv("MAX_TOKENS")
max_tokens = 100 if max_tokens is None else int(max_tokens)

robot = werobot.WeRoBot(token=os.getenv("WECHAT_TOKEN"))
messages = [ {"role": "system", "content": "Your are an AI assitant."}]
messages_tokens = len(messages[0]["content"])

def get_gpt3_reply(text):
    print("Calling text-davinci-003 API...")
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=text,
        max_tokens=max_tokens,
        temperature=0,
    )
    return response.choices[0].text.strip()

def get_gpt3dot5_reply(prompt):
    print("Calling gpt-3.5-turbo API...")
    global messages, messages_tokens
    messages.append({"role":"user", "content": prompt})
    messages_tokens += len(prompt)
    if len(messages) > 10 or messages_tokens > 256:
        messages.pop(0)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.8
    )

    messages.append(response.choices[0].message)
    messages_tokens += len(response.choices[0].message.content)
    return response.choices[0].message.content.strip()

@robot.text
def hello_world(message):
    if (os.getenv("GPT_MODEL_VERSION") == "3"):
        reply = get_gpt3_reply(message.content)
    else:
        reply = get_gpt3dot5_reply(message.content)
        
    # print(reply)
    return reply

wechat = Blueprint('wechat', __name__)

# Router
@wechat.route('/')
def index():
    return 'Web App with Python Flask!'

wechat.add_url_rule(rule='/robot/', # WeRoBot 的绑定地址
                endpoint='werobot', # Flask 的 endpoint
                view_func=make_view(robot),
                methods=['GET', 'POST'])

if  __name__ == "__main__":
    wechat.run(host='127.0.0.1', port=8080)