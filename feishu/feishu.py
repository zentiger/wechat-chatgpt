#!/usr/bin/env python3.8

import os
import logging
import requests
from .api import MessageApiClient
from .event import MessageReceiveEvent, UrlVerificationEvent, EventManager
from flask import Flask, jsonify, Blueprint
from dotenv import load_dotenv, find_dotenv
import openai
import json

# load env parameters form file named .env
load_dotenv(find_dotenv())

feishu = Blueprint('feishu', __name__)

# load from env
##  env for lark
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
VERIFICATION_TOKEN = os.getenv("VERIFICATION_TOKEN")
ENCRYPT_KEY = os.getenv("ENCRYPT_KEY")
LARK_HOST = os.getenv("LARK_HOST")

## env for openai
openai.api_key = os.getenv("OPENAI_API_KEY")
max_tokens = os.getenv("MAX_TOKENS")
max_tokens = 100 if max_tokens is None else int(max_tokens)

# init chatgpt api
chatgpt_messages = [ {"role": "system", "content": "Your are an AI assitant."}]
chatgpt_messages_tokens = len(chatgpt_messages[0]["content"])

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

    global chatgpt_messages, chatgpt_messages_tokens
    chatgpt_messages.append({"role":"user", "content": prompt})
    chatgpt_messages_tokens += len(prompt)

    if len(chatgpt_messages) > 10 or chatgpt_messages_tokens > 256:
        chatgpt_messages.pop(0)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=chatgpt_messages,
        max_tokens=max_tokens,
        temperature=0.8
    )

    chatgpt_messages.append(response.choices[0].message)
    chatgpt_messages_tokens += len(response.choices[0].message.content)
    return response.choices[0].message.content.strip()

# init lark service
message_api_client = MessageApiClient(APP_ID, APP_SECRET, LARK_HOST)
event_manager = EventManager()


@event_manager.register("url_verification")
def request_url_verify_handler(req_data: UrlVerificationEvent):
    # url verification, just need return challenge
    if req_data.event.token != VERIFICATION_TOKEN:
        raise Exception("VERIFICATION_TOKEN is invalid")
    return jsonify({"challenge": req_data.event.challenge})


@event_manager.register("im.message.receive_v1")
def message_receive_event_handler(req_data: MessageReceiveEvent):
    sender_id = req_data.event.sender.sender_id
    message = req_data.event.message
    if message.message_type != "text":
        logging.warn("Other types of messages have not been processed yet")
        return jsonify()
        # get open_id and text_content
    open_id = sender_id.open_id
    prompt = message.content
    # echo text message

    chatgpt_reply = get_gpt3dot5_reply(json.loads(prompt)["text"])
    message_api_client.send_text_with_open_id(open_id, json.dumps({"text": chatgpt_reply}))
    return jsonify()


@feishu.errorhandler
def msg_error_handler(ex):
    logging.error(ex)
    response = jsonify(message=str(ex))
    response.status_code = (
        ex.response.status_code if isinstance(ex, requests.HTTPError) else 500
    )
    return response


@feishu.route("/", methods=["POST"])
def callback_event_handler():
    # init callback instance and handle
    event_handler, event = event_manager.get_handler_with_event(VERIFICATION_TOKEN, ENCRYPT_KEY)

    return event_handler(event)

if __name__ == "__main__":
    # init()
    feishu.run(host="0.0.0.0", port=3000, debug=True)
