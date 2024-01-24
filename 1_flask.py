# read .env files
import dotenv, os
dotenv.load_dotenv()

# start a flask app
from flask import Flask, request, jsonify

flask_app = Flask(__name__)

# this is the challenge route required by Slack to add perms
@flask_app.route("/", methods=["POST"])
def slack_challenge():
    if request.json and "challenge" in request.json:
        print("Received challenge")
        return jsonify({"challenge": request.json["challenge"]})
    else:
        print("Got unknown request incoming")
        print(request.json)
    return

if __name__ == "__main__":
    flask_app.run(port=3000)
