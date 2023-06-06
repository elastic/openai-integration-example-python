from elasticsearch import Elasticsearch
from flask import Flask, render_template, request
import requests
import os

global OPTIONS

INDEX = 'openai-integration'
MODEL = 'text-embedding-ada-002'
ELASTIC_CLOUD_ID = os.getenv('ELASTIC_CLOUD_ID')
ELASTIC_USERNAME = os.getenv('ELASTIC_USERNAME')
ELASTIC_PASSWORD = os.getenv('ELASTIC_PASSWORD')
OPENAI_API_TOKEN = os.getenv('OPENAI_API_TOKEN')

app = Flask(__name__)


@app.route("/")
def route_main():
    return render_template('search.html', hits=[])


@app.route("/search")
def route_search():
    query = request.args.get('q')

    search_result = run_semantic_search(query)
    hits = []
    for hit in search_result['hits']['hits']:
        source = hit['_source']
        hits.append({
            '_id': hit['_id'],
            'score': hit['_score'],
            'title': source['title'],
            'content': source['content'],
            'url': source['url']
        })

    return render_template('search.html', query=query, hits=hits)


def generate_embedding_with_openai(text):
    url = 'https://api.openai.com/v1/embeddings'
    headers = {
        'Authorization': f'Bearer {OPENAI_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    body = {
        'input': text,
        'model': MODEL
    }
    response = requests.post(url, json=body, headers=headers)

    if not response.ok:
        raise Exception('Error while using OpenAI API: ' + response.json()['error']['message'])

    return response.json()['data'][0]['embedding']


def run_semantic_search(query):
    if query is None or query.strip() == '':
        raise Exception('Missing query')

    # Generate OpenAI embedding for query
    embedding = generate_embedding_with_openai(query)
    knn = {
        'field': 'embedding',
        'query_vector': embedding,
        'k': 10,
        'num_candidates': 100
    }
    result = es_client.search(index=INDEX, knn=knn, source=['url', 'title', 'content'], size=10)

    return result.body


if __name__ == '__main__':
    print(f'Connecting to Elastic Cloud: {ELASTIC_CLOUD_ID}')

    es_client = Elasticsearch(cloud_id=ELASTIC_CLOUD_ID, basic_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD))

    print(f'Starting Flask app')

    app.run(host='127.0.0.1', port=8080, debug=True)
