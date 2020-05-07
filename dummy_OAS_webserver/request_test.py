from __future__ import print_function
import openapi_client
import time
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint
# Defining the host is optional and defaults to http://localhost:8000
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost:8000"
)
def list_top_k():
    # #{
    # Enter a context with an instance of the API client
    with openapi_client.ApiClient() as api_client:
        # Create an instance of the API class
        api_instance = openapi_client.DefaultApi(api_client)
        language = 'en' # str | language of the vocabulary
        number_of_words = 56 # int | How many top words return at one time (max 100)

        try:
            # List all words
            api_response = api_instance.list_top_k(language, number_of_words)
            pprint(api_response)
            return api_response
        except ApiException as e:
            print("Exception when calling DefaultApi->list_top_k: %s\n" % e)
# #}

def wordembeddings(l):
    # Enter a context with an instance of the API client#{
    with openapi_client.ApiClient() as api_client:
        api_instance = openapi_client.DefaultApi(api_client)
        number_of_dimensions = 56 # int | How many dim in the wordembeddings
        request_body = l# list[str] | 

        try:
            # calculate word embeddings for each sentence in as list of sentences
            api_response = api_instance.calculate_word_embeddings(number_of_dimensions, request_body)
            pprint(api_response)
        except ApiException as e:
            print("Exception when calling DefaultApi->calculate_word_embeddings: %s\n" % e)

list_=list_top_k()
wordembeddings(list_)
