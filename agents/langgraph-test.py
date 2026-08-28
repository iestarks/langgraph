from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# 1. Define the state shape
class State(TypedDict):
    input_text: str
    reply: str

# 2. Create node functions that modify state
def my_node(state: State):
    return {"reply": f"Processed: {state['input_text']}"}

# 3. Build and compile the graph
builder = StateGraph(State)
builder.add_node("processor", my_node)
builder.add_edge(START, "processor")
builder.add_edge("processor", END)

graph = builder.compile()

if __name__ == "__main__":
    result = graph.invoke({"input_text": "hello world"})
    print(result)
