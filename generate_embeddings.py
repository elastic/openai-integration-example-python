from elasticsearch import Elasticsearch, helpers
import json
import os
import requests

FILE = 'sample_data/medicare.json'
INDEX = 'openai-integration'
MODEL = 'text-embedding-ada-002'
ELASTIC_CLOUD_ID = os.getenv('ELASTIC_CLOUD_ID')
ELASTIC_USERNAME = os.getenv('ELASTIC_USERNAME')
ELASTIC_PASSWORD = os.getenv('ELASTIC_PASSWORD')
OPENAI_API_TOKEN = os.getenv('OPENAI_API_TOKEN')


def bulk_index_docs(docs, es_client):
    actions = []
    for doc in docs:
        action = {
            "_op_type": "index",
            "_index": INDEX,
            "_id": doc["url"],
            "_source": doc,
        }
        actions.append(action)

    print(f"Indexing {len(docs)} documents to index {INDEX}...")

    try:
        helpers.bulk(es_client, actions)
    except Exception as e:
        print(f'Error while indexing documents: {e}')
        exit(1)


def generate_embeddings_with_openai(docs):
    print(f'Calling OpenAI API for {len(docs)} embeddings with model {MODEL}')

    input = [doc['content'] for doc in docs]
    url = 'https://api.openai.com/v1/embeddings'
    headers = {
        'Authorization': f'Bearer {OPENAI_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    body = {
        'input': input,
        'model': MODEL
    }

    response = requests.post(url, json=body, headers=headers)
    if response.ok:
        return [data['embedding'] for data in response.json()['data']]
    else:
        raise Exception('Error while using OpenAI API: ' + response.json()['error']['message'])


def process_file():
    print(f'Reading from file {FILE}')

    with open(FILE, 'r') as in_file:
        docs = json.load(in_file)

        print(f'Processing {len(docs)} documents...')

        # Split the list of documents into batches of 10
        batch_size = 10
        docs_batches = [docs[i:i + batch_size] for i in range(0, len(docs), batch_size)]
        for docs_batch in docs_batches:
            print(f'Processing batch of {len(docs_batch)} documents...')
            
            # Generate embeddings and add them to the documents
            embeddings = generate_embeddings_with_openai(docs_batch)
            for i, doc in enumerate(docs_batch):
                doc['embedding'] = embeddings[i]

            # Index batch of documents
            bulk_index_docs(docs_batch, es_client)

            # Uncomment this if you're hitting the OpenAI rate limit due to the number of requests
            # print('Sleeping for 2 seconds to avoid reaching OpenAI rate limit...')
            # time.sleep(2)

    print('Processing complete')


if __name__ == "__main__":
    print(f'Connecting to Elastic Cloud: {ELASTIC_CLOUD_ID}')

    es_client = Elasticsearch(cloud_id=ELASTIC_CLOUD_ID, basic_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD))

    process_file()
