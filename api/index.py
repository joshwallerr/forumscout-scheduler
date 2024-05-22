from flask import Flask, redirect, request
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from github import Github, GithubException
from bson import ObjectId
import urllib.parse
import json
from cryptography.fernet import Fernet
import base64

app = Flask(__name__)

app.config["MONGO_URI"] = os.environ.get('MONGODB_URI')
client = MongoClient(app.config["MONGO_URI"], server_api=ServerApi('1'))
db = client.forumscout
users = db.users
scouts = db.scouts


key = os.environ.get('ENCRYPTION_KEY')
cipher_suite = Fernet(key)


def encrypt_data(data):
    """Encrypts data and returns a base64-encoded string."""
    encrypted_data = cipher_suite.encrypt(data.encode())
    return base64.b64encode(encrypted_data).decode('utf-8')

def decrypt_data(encrypted_data):
    """Decrypts data from a base64-encoded string."""
    try:
        base64_decoded = base64.b64decode(encrypted_data)
        return cipher_suite.decrypt(base64_decoded).decode('utf-8')
    except Exception as e:
        print(f"Decryption failed: {e}")
        return None






@app.route('/')
def home():
    return redirect('https://forumscout.app', code=301)





@app.route('/create-action', methods=['POST'])
def create_action():
    email = request.json['owner']
    country = request.json['country']
    query = request.json['query']

    # Get the user from the database
    user = users.find_one({'email': email})
    
    # Get the scout from the database
    scout = scouts.find_one({'query': query, 'country': country})

    if scout and user:
        create_github_action(scout)
        return "GitHub Action created successfully"
    else:
        return "User or scout not found"



@app.route('/delete-action', methods=['POST'])
def delete_action():
    email = request.json['owner']
    country = request.json['country']
    query = request.json['query']
    scout_id = request.json['id']

    # Get the user from the database
    user = users.find_one({'email': email})
    
    # Get the scout from the database
    scout = scouts.find_one({'_id': ObjectId(scout_id)})

    if scout and user:
        delete_github_action(scout)
        return "GitHub Action deleted successfully"
    else:
        return "User or scout not found"




def delete_github_action(scout):
    token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_REPO_NAME')
    g = Github(token)
    repo = g.get_user().get_repo(repo_name)

    user = users.find_one({'email': scout['owner']})

    encrypted_query = encrypt_data(scout['query'])

    # safe_query = urllib.parse.quote(scout['query'].replace(' ', '_'), safe='')

    path = f".github/workflows/run_scout_{encrypted_query}_{scout['country']}_{str(user['_id'])}.yml"

    try:
        contents = repo.get_contents(path)
        repo.delete_file(contents.path, f"Delete action for scout {encrypted_query}", contents.sha, branch="main")
        scouts.delete_one({'_id': scout['_id']})
    except GithubException as e:
        return 'error: ' + str(e)

    return "GitHub Action deleted successfully!"





def create_github_action(scout):
    token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_REPO_NAME')
    g = Github(token)
    repo = g.get_user().get_repo(repo_name)

    user = users.find_one({'email': scout['owner']})

    encrypted_query = encrypt_data(scout['query'])

    data_json = json.dumps({
        "owner": str(user['_id']),
        "query": encrypted_query,
        "country": scout['country']
    })

    # Generate the GitHub Action workflow content
    workflow_content = f"""
name: Run Scout {encrypted_query}

on:
  schedule:
    - cron:  '0 * * * *'

jobs:
  run-scout:
    runs-on: ubuntu-latest
    steps:
      - name: Send POST request
        uses: fjogeleit/http-request-action@master
        with:
          url: 'https://forumscout.app/run-scout'
          method: 'POST'
          contentType: 'application/json'
          data: '{data_json}'
    """

    # safe_query = urllib.parse.quote(scout['query'].replace(' ', '_'), safe='')
    path = f".github/workflows/run_scout_{encrypted_query}_{scout['country']}_{str(user['_id'])}.yml"

    try:
        repo.create_file(path, f"Create action for scout {encrypted_query}", workflow_content, branch="main")
    except GithubException as e:
        return 'File already exists!'

    return "GitHub Action created successfully!"



# implement scout management - ADD, DELETE, EDIT.

# implement feed




if __name__ == '__main__':
    app.run(debug=True)