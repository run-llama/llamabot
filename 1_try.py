import dotenv
dotenv.load_dotenv()

from llama_index.tools import FunctionTool
from llama_index.llms import OpenAI
from llama_index.agent import OpenAIAgent

# define sample Tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers and returns the result integer"""
    return a * b


multiply_tool = FunctionTool.from_defaults(fn=multiply)

# initialize llm
llm = OpenAI(model="gpt-4")

# initialize ReAct agent
agent = OpenAIAgent.from_tools([multiply_tool], llm=llm, verbose=True)
response = agent.query("multiply 2 and 3")

print(response)
