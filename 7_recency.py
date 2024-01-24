# read .env files
import dotenv, os
dotenv.load_dotenv()

import datetime, uuid

# Bring in deps including Slack Bolt framework
from slack_bolt import App
from slack_sdk import WebClient
from flask import Flask, request, jsonify
from slack_bolt.adapter.flask import SlackRequestHandler

# bring in llamaindex deps
import qdrant_client
from llama_index import VectorStoreIndex, Document, StorageContext, ServiceContext, set_global_handler
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.schema import TextNode
from llama_index.prompts import PromptTemplate
from llama_index.postprocessor import FixedRecencyPostprocessor

# turn on debugging
set_global_handler("simple")

# initialize qdrant client and a vector store that uses it
client = qdrant_client.QdrantClient(
    path="./qdrant_data"
)
vector_store = QdrantVectorStore(client=client, collection_name="tweets")
storage_context = StorageContext.from_defaults(vector_store=vector_store)

index = VectorStoreIndex([],storage_context=storage_context)

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

# get the bot's own user ID so it can tell when somebody is mentioning it
auth_response = app.client.auth_test()
bot_user_id = auth_response["user_id"]

# given a query and a message, answer the question and return the response
def answer_question(query, message, replies=None):
    template = (
        "Your context is a series of chat messages. Each one is tagged with 'who:' \n"
        "indicating who was speaking and 'when:' indicating when they said it, \n"
        "followed by a line break and then what they said. There can be up to 20 chat messages.\n"
        "The messages are sorted by recency, so the most recent one is first in the list.\n"
        "The most recent messages should take precedence over older ones.\n"
        "---------------------\n"
        "{context_str}"
        "\n---------------------\n"
        "You are a helpful AI assistant who has been listening to everything everyone has been saying. \n"
        "Given the most relevant chat messages above, please answer this question: {query_str}\n"
    )
    qa_template = PromptTemplate(template)                                
    postprocessor = FixedRecencyPostprocessor(
        top_k=20, 
        date_key="when", # the key in the metadata to find the date
        service_context=ServiceContext.from_defaults()
    )
    query_engine = index.as_query_engine(similarity_top_k=20, node_postprocessors=[postprocessor])
    query_engine.update_prompts(
        {"response_synthesizer:text_qa_template": qa_template}
    )
    return query_engine.query(query)


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

# this handles any incoming message the bot can hear
# we want it to only respond when somebody messages it directly
# otherwise it listens and stores every message as future context
@app.message()
def reply(message, say):
    # the slack message object is a complicated nested object
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
    #                       then it's a message for the bot
    if message.get('blocks'):
        for block in message.get('blocks'):
            if block.get('type') == 'rich_text':
                for rich_text_section in block.get('elements'):
                    for element in rich_text_section.get('elements'):
                        if element.get('type') == 'user' and element.get('user_id') == bot_user_id:
                            for element in rich_text_section.get('elements'):
                                if element.get('type') == 'text':
                                    query = element.get('text')
                                    print(f"Somebody asked the bot: {query}")
                                    response = answer_question(query,message)
                                    print("Context was:")
                                    print(response.source_nodes)
                                    print(f"Response was: {response}")
                                    say(str(response))
                                    return
    # if it's not any kind of question, we store it in the index along with all relevant metadata

    # get message timestamp and format as YYYY-MM-DD HH:MM:SS
    dt_object = datetime.datetime.fromtimestamp(float(message.get('ts')))
    formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')

    # get the message text
    text = message.get('text')

    # create a node with metadata
    node = TextNode(
        text=text,
        id_=str(uuid.uuid4()),
        metadata={
            "when": formatted_time
        }
    )
    index.insert_nodes([node])
    print("Stored message", message.get('text'))

if __name__ == "__main__":
    flask_app.run(port=3000)
