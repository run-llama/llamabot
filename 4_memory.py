import dotenv, os
dotenv.load_dotenv()

from slack_bolt import App
from slack_sdk import WebClient
from flask import Flask, request, jsonify
from slack_bolt.adapter.flask import SlackRequestHandler

from llama_index import VectorStoreIndex, Document

index = VectorStoreIndex([])

# Initialize your app with your bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(app)
flask_app = Flask(__name__)

# join the test channel so you can listen to messages
channel_list = app.client.conversations_list().data
channel = next((channel for channel in channel_list.get('channels') if channel.get("name") == "bot-testing"), None)
channel_id = channel.get('id')
app.client.conversations_join(channel=channel_id)

# get my own ID
auth_response = app.client.auth_test()
print(auth_response)
bot_user_id = auth_response["user_id"]

# this is the challenge route required by Slack
# if it's not the challenge it's something for Bolt to handle
# (why doesn't Bolt handle the challenge? It's their framework, they should know the challenge is coming...)
@flask_app.route("/", methods=["POST"])
def slack_challenge():
    if request.json and "challenge" in request.json:
        print("Received challenge")
        return jsonify({"challenge": request.json["challenge"]})
    else:
        print("Incoming event:")
        print(request.json)
    return handler.handle(request)

# this handles any incoming message the bot can hear
# right now it's only in one channel so it's every message in that channel
@app.message()
def reply(message, say):
    # if message contains a "blocks" key
    #   then look for a "block" with the type "rich text"
    #       if you find it 
    #       then look inside that block for an "elements" key
    #           if you find it 
    #               then examine each one of those for an "elements" key
    #               if you find it
    #                   then look inside each "element" for one with type "user"
    #                   if you find it  
    #                   and if that user matches the bot_user_id 
    #                   then it's a message from the bot
    if message.get('blocks'):
        for block in message.get('blocks'):
            if block.get('type') == 'rich_text':
                for rich_text_section in block.get('elements'):
                    for element in rich_text_section.get('elements'):
                        if element.get('type') == 'user' and element.get('user_id') == bot_user_id:
                            for element in rich_text_section.get('elements'):
                                if element.get('type') == 'text':
                                    query = element.get('text')
                                    print("Using query", query)
                                    query_engine = index.as_query_engine()
                                    response = query_engine.query(query)
                                    print(response)
                                    say(str(response))
                                    return
    # otherwise treat it as a document to store
    index.insert(Document(text=message.get('text')))
    print("Stored message", message.get('text'))

if __name__ == "__main__":
    flask_app.run(port=3000)
