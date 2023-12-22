# env first
import dotenv
dotenv.load_dotenv()

# slack app deps
import os
from slack_bolt import App
from slack_sdk import WebClient
from flask import Flask, request, jsonify
from slack_bolt.adapter.flask import SlackRequestHandler

# RAG app deps
import qdrant_client
from llama_index import VectorStoreIndex, Document, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore

# initialize qdrant client
client = qdrant_client.QdrantClient(
    path="./qdrant_data"
)
vector_store = QdrantVectorStore(client=client, collection_name="tweets")
storage_context = StorageContext.from_defaults(vector_store=vector_store)

index = VectorStoreIndex([],storage_context=storage_context)

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

# get a user's username and display name from their user id
def get_user_name(user_id):
    user_info = app.client.users_info(user=user_id)
    user_name = user_info['user']['name']
    user_display_name = user_info['user']['profile']['display_name']
    return user_name, user_display_name

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
    # if it's not a question, we store it in the index along with all relevant metadata
    user_name, user_display_name = get_user_name(message.get('user'))
    text = user_display_name + " said " + message.get('text')
    index.insert(Document(text=text))
    print("Stored message:", text)

if __name__ == "__main__":
    flask_app.run(port=3000)
