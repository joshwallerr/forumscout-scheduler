from flask import Flask, redirect
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os





app = Flask(__name__)

app.config["MONGO_URI"] = os.environ.get('MONGODB_URI')
client = MongoClient(app.config["MONGO_URI"], server_api=ServerApi('1'))
db = client.forumscout
users = db.users
scouts = db.scouts




@app.route('/')
def home():
    return redirect('https://forumscout.app', code=301)



@app.route('/run-scout', methods=['POST'])
def run_scout():
    email = request.json['email']
    query = request.json['query']
    
    user = users.find_one({'email': email})




    return "Scout ran successfully"








if __name__ == '__main__':
    app.run(debug=True)