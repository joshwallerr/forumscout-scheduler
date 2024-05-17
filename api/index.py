from flask import Flask, redirect, request
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from github import Github



app = Flask(__name__)

app.config["MONGO_URI"] = os.environ.get('MONGODB_URI')
client = MongoClient(app.config["MONGO_URI"], server_api=ServerApi('1'))
db = client.forumscout
users = db.users
scouts = db.scouts




@app.route('/')
def home():
    return redirect('https://forumscout.app', code=301)



# @app.route('/run-scout', methods=['POST'])
# def run_scout():
#     email = request.json['email']
#     query = request.json['query']
    
#     user = users.find_one({'email': email})




#     return "Scout ran successfully"


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











def create_github_action(scout):
    token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_REPO_NAME')
    g = Github(token)
    repo = g.get_user().get_repo(repo_name)

    # Generate the GitHub Action workflow content
    workflow_content = f"""
name: Run Scout {scout['query']}

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
          url: 'https://yourdomain.com/run-scout'
          method: 'POST'
          contentType: 'application/json'
          data: '{{
            "owner": "{scout['owner']}",
            "query": "{scout['query']}",
            "country": "{scout['country']}"
          }}'
    """

    # Path where the GitHub Action will be saved - NEEDS TO BE CHANGED?
    path = f".github/workflows/run_scout_{scout['query'].replace(' ', '_')}_{scout['country']}.yml"

    try:
        repo.create_file(path, f"Create action for scout {scout['query']}", workflow_content, branch="main")
    except GithubException as e:
        return 'File already exists!'

    return "GitHub Action created successfully!"



# In /run-scouts get all scouts that have that query and add results for all of them.

# What if query containes unique characters? How to handle that?


if __name__ == '__main__':
    app.run(debug=True)