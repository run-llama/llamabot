# bring in llamaindex deps, debugging, and .env
import dotenv
import logging
import sys
dotenv.load_dotenv()

from llama_index import VectorStoreIndex, Document, set_global_handler

# turns on debuging
set_global_handler("simple")

# even noisier debugging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# initialize index
index = VectorStoreIndex([])

# create documents
doc1 = Document(text="Molly is a cat")
doc2 = Document(text="Doug is a dog")
doc3 = Document(text="Carl is a rat")

# add all 3 to the index
index.insert(doc1)
index.insert(doc2)
index.insert(doc3)

# run a query
query_engine = index.as_query_engine()
response = query_engine.query("Who is Molly?")
print(response)
