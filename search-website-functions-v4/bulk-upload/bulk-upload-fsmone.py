import sys
import json
import requests
import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex
from azure.search.documents.indexes.models import (
    ComplexField,
    CorsOptions,
    SearchIndex,
    ScoringProfile,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
)

# Get the service name (short name) and admin API key from the environment
service_name = "aisrch-poc-uscentral-01"
key = "XE8nyqGGhtVXqmSlsrJPW0yEMiHocP7dWwktdCSclpAzSeATbtHu"
endpoint = "https://{}.search.windows.net/".format(service_name)

# Give your index a name
# You can also supply this at runtime in __main__
index_name = "fsmone-sg123"

# Search Index Schema definition
index_schema = "./dict_prodName-schema.json"

batch_size = 1000
with open("./dict_prodName.json") as file:
    product_data = json.load(file)

# Instantiate a client
class CreateClient(object):
    def __init__(self, endpoint, key, index_name):
        self.endpoint = endpoint
        self.index_name = index_name
        self.key = key
        self.credentials = AzureKeyCredential(key)

    # Create a SearchClient
    # Use this to upload docs to the Index
    def create_search_client(self):
        return SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credentials,
        )

    # Create a SearchIndexClient
    # This is used to create, manage, and delete an index
    def create_admin_client(self):
        return SearchIndexClient(endpoint=endpoint, credential=self.credentials)


# Get Schema from File or URL
def get_schema_data(schema, url=False):
    if not url:
        with open(schema) as json_file:
            schema_data = json.load(json_file)
            return schema_data
    else:
        data_from_url = requests.get(schema)
        schema_data = json.loads(data_from_url.content)
        return schema_data


# Create Search Index from the schema
# If reading the schema from a URL, set url=True
def create_schema_from_json_and_upload(schema, index_name, admin_client, url=False):

    cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=60)
    scoring_profiles = []
    schema_data = get_schema_data(schema, False)

    index = SearchIndex(
        name=index_name,
        fields=schema_data["fields"],
        scoring_profiles=scoring_profiles,
        suggesters=schema_data["suggesters"],
        cors_options=cors_options,
    )

    try:
        upload_schema = admin_client.create_index(index)
        if upload_schema:
            print(f"Schema uploaded; Index created for {index_name}.")
        else:
            exit(0)
    except:
        print("Unexpected error:", sys.exc_info()[0])


# Convert CSV data to JSON
def convert_csv_to_json(url):
    df = pd.read_csv(url)
    convert = df.to_json(orient="records")
    return json.loads(convert)


# Batch your uploads to Azure Search
def batch_upload_json_data_to_index(json_file, client):
    batch_array = []
    count = 0
    batch_counter = 0
    for i in json_file:
        count += 1
        batch_array.append(i)

        # In this sample, we limit batches to 1000 records.
        # When the counter hits a number divisible by 1000, the batch is sent.
        if count % batch_size == 0:
            client.upload_documents(documents=batch_array)
            batch_counter += 1
            print(f"Batch sent! - #{batch_counter}")
            batch_array = []

    # This will catch any records left over, when not divisible by 1000
    if len(batch_array) > 0:
        client.upload_documents(documents=batch_array)
        batch_counter += 1
        print(f"Final batch sent! - #{batch_counter}")

    print("Done!")


if __name__ == "__main__":
    start_client = CreateClient(endpoint, key, index_name)
    admin_client = start_client.create_admin_client()
    search_client = start_client.create_search_client()
    schema = create_schema_from_json_and_upload(
        index_schema, index_name, admin_client, url=False
    )
    print(schema)
    batch_upload = batch_upload_json_data_to_index(product_data, search_client)
    print("Upload complete")