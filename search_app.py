from elasticsearch import Elasticsearch
from flask import Flask, render_template, request
from openai import Embedding
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


def generate_embeddings_with_openai(text):
    print(f'Calling OpenAI API for embedding with model {MODEL}')

    try:
        result = Embedding.create(engine=MODEL, input=text)
        return result['data'][0]['embedding']
    except Exception as e:
        print(f'Error while calling OpenAI API: {e}')
        exit(1)


def run_semantic_search(query):
    if query is None or query.strip() == '':
        raise Exception('Missing query')

    # Generate OpenAI embedding for query
    embedding = generate_embeddings_with_openai(query)
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
