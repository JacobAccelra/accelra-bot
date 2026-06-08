import os
import logging
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

CLIENT_CHANNELS = {
    "C0B7YJCFB24",
    "C0B77TJFQCC",
    "C0B6NRL08NB",
}

CLIENT_CHANNEL_PREFIX = "accelra-"
WELCOME_INTERNAL = "Welcome to the channel, <@{user}>!"
WELCOME_CLIENT = "Welcome, <@{user}>! This is your direct line to the Accelra team. Drop any questions, requests, or updates right here and we will take care of it."
CLIENT_ONBOARDING = "Welcome to your Accelra channel - this is your dedicated space for your project. Questions, requests, updates - drop it here and we will take it from there. Support hours: Mon-Fri, 7am-7pm CST."
AUTO_REPLY = "Got it - we have received your message and will follow up within a few hours. Support hours: Mon-Fri, 7am-7pm CST. If after hours, we will pick it up the next business day."

def post(channel, text, thread_ts=None):
    try:
        kwargs = {"channel": channel, "text": text}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        client.chat_postMessage(**kwargs)
    except SlackApiError as e:
        logging.error(f"Slack error in {channel}: {e.response['error']}")

def handle_member_joined(event):
    channel_id = event.get("channel")
    user_id = event.get("user")
    bot_user_id = os.environ.get("BOT_USER_ID", "")
    if user_id == bot_user_id:
        return
    if channel_id in CLIENT_CHANNELS:
        post(channel_id, WELCOME_CLIENT.format(user=user_id))
    else:
        post(channel_id, WELCOME_INTERNAL.format(user=user_id))

def handle_message(event):
    channel_id = event.get("channel")
    ts = event.get("ts")
    thread_ts = event.get("thread_ts")
    if channel_id not in CLIENT_CHANNELS:
        return
    if event.get("bot_id") or event.get("subtype"):
        return
    if thread_ts and thread_ts != ts:
        return
    post(channel_id, AUTO_REPLY, thread_ts=ts)

def handle_channel_created(event):
    channel = event.get("channel", {})
    channel_id = channel.get("id")
    channel_name = channel.get("name", "")
    if channel_name.startswith(CLIENT_CHANNEL_PREFIX):
        CLIENT_CHANNELS.add(channel_id)
        post(channel_id, CLIENT_ONBOARDING)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        event_type = event.get("type")
        if event_type == "member_joined_channel":
            handle_member_joined(event)
        elif event_type == "message":
            handle_message(event)
        elif event_type == "channel_created":
            handle_channel_created(event)
    return jsonify({"ok": True})

@app.route("/", methods=["GET"])
def health():
    return "Accelra Bot is running.", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
