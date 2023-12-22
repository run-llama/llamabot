import dotenv
import logging
import sys
dotenv.load_dotenv()

from llama_index import VectorStoreIndex, Document, set_global_handler

set_global_handler("simple")

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

index = VectorStoreIndex([])

doc1 = Document(text="Molly is a cat")
doc2 = Document(text="Doug is a dog")
doc3 = Document(text="Carl is a rat")

index.insert(doc1)

query_engine = index.as_query_engine()
response = query_engine.query("Who is Molly?")
print(response)
