# read .env files
import dotenv, os
dotenv.load_dotenv()

# Bring in deps including Slack Bolt framework
from slack_bolt import App
from flask import Flask, request, jsonify
from slack_bolt.adapter.flask import SlackRequestHandler

# Initialize Bolt app with token and secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(app)

# start flask app
flask_app = Flask(__name__)

# join the #bot-testing channel so we can listen to messages
channel_list = app.client.conversations_list().data
channel = next((channel for channel in channel_list.get('channels') if channel.get("name") == "bot-testing"), None)
channel_id = channel.get('id')
app.client.conversations_join(channel=channel_id)
print(f"Found the channel {channel_id} and joined it")

# this is the challenge route required by Slack
# if it's not the challenge it's something for Bolt to handle
@flask_app.route("/", methods=["POST"])
def slack_challenge():
    if request.json and "challenge" in request.json:
        print("Received challenge")
        return jsonify({"challenge": request.json["challenge"]})
    else:
        print("Incoming event:")
        print(request.json)
    return handler.handle(request)

# Bolt conveniently splits up events into types, like messages
# this handles any incoming message the bot can hear
# and replies to every single message with yes
@app.message()
def reply(message, say):
    print(message)
    say("Yes?")

if __name__ == "__main__":
    flask_app.run(port=3000)
