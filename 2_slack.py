import dotenv, os
dotenv.load_dotenv()

# Use the package we installed
from slack_bolt import App
from slack_sdk import WebClient
from flask import Flask, request, jsonify
from slack_bolt.adapter.flask import SlackRequestHandler

# Initialize your app with your bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(app)
flask_app = Flask(__name__)

# initialize client also with the bot token
slack_token = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=slack_token)

# join the channel so you can listen to messages
channel_list = client.conversations_list().data
channel = next((channel for channel in channel_list.get('channels') if channel.get("name") == "bot-testing"), None)
channel_id = channel.get('id')
client.conversations_join(channel=channel_id)

# this is the challenge route required by Slack
@flask_app.route("/", methods=["POST"])
def slack_challenge():
    if request.json and "challenge" in request.json:
        print("Received challenge")
        return jsonify({"challenge": request.json["challenge"]})
    else:
        print("Got unknown request incoming")
        print(request.json)
    return handler.handle(request)

# this handles any incoming message the bot can hear
@app.message()
def reply(message, say):
    print(message)
    say("Yes?")

if __name__ == "__main__":
    flask_app.run(port=3000)
