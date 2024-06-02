from flask import Flask, redirect, request, jsonify
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from github import Github, GithubException
from bson import ObjectId
import urllib.parse
import json
from cryptography.fernet import Fernet
import base64
from requests import post
from urllib.parse import quote
import time

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
    scout_id = request.json['id']

    # Get the user from the database
    user = users.find_one({'email': email})
    
    # Get the scout from the database
    scout = scouts.find_one({'_id': ObjectId(scout_id)})

    if scout and user:
        create_github_action(scout)
        return jsonify({"message": "GitHub Action created successfully"}), 200
    else:
        return jsonify({"message": "User or scout not found"}), 404



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
        return jsonify({"message": "GitHub Action deleted successfully"}), 200
    else:
        return jsonify({"message": "User or scout not found"}), 404




def delete_github_action(scout):
    token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_REPO_NAME')
    g = Github(token)
    repo = g.get_user().get_repo(repo_name)

    user = users.find_one({'email': scout['owner']})

    # Using ObjectId (or another unique, consistent scout identifier) in the file path
    path = f".github/workflows/run_scout_{scout['_id']}.yml"

    try:
        contents = repo.get_contents(path)
        repo.delete_file(contents.path, f"Delete action for scout {scout['query']}", contents.sha, branch="main")
        scouts.delete_one({'_id': scout['_id']})
        return "GitHub Action deleted successfully!"
    except GithubException as e:
        print(e)
        return 'File not found!'






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
name: Run Scout {scout['_id']}

on:
  schedule:
    - cron:  '0 * * * *'
  workflow_dispatch:

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
          timeout: 15000
    """

    # safe_query = urllib.parse.quote(scout['query'].replace(' ', '_'), safe='')
    path = f".github/workflows/run_scout_{scout['_id']}.yml"

    try:
        repo.create_file(path, f"Create action for scout {scout['_id']}", workflow_content, branch="main")
    except GithubException as e:
        return 'File already exists!'

    # time.sleep(10)

    # # run the action immediately here
    # trigger_github_action(repo, scout)

    return "GitHub Action created successfully!"




def trigger_github_action(repo, scout):
    # URL-encode the workflow file name (excluding '.yml')
    workflow_file_name = f"run_scout_{scout['_id']}"
    encoded_workflow_file_name = quote(workflow_file_name + '.yml')  # Including '.yml' because GitHub uses the filename

    print(f"Repository Full Name: {repo.full_name}")
    print(f"Workflow File Name: {workflow_file_name}")
    print(f"Encoded Workflow File Name: {encoded_workflow_file_name}")

    # Define the API URL using the encoded workflow file name
    url = f"https://api.github.com/repos/{repo.full_name}/actions/workflows/{encoded_workflow_file_name}/dispatches"

    print(f"API URL: {url}")

    # Setup the headers and data payload
    headers = {
        'Authorization': f'token {os.environ.get("GITHUB_TOKEN")}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    data = {
        'ref': 'main',  # Adjust this to the branch where the workflow file resides
    }

    # Make the API request
    response = post(url, headers=headers, json=data)
    if response.status_code == 204:
        print("Action triggered successfully!")
        return "Action triggered successfully!"
    else:
        print(f"Failed to trigger action: {response.content.decode()}")  # Decode to make it readable
        return f"Failed to trigger action: {response.content.decode()}"




if __name__ == '__main__':
    app.run(debug=True)