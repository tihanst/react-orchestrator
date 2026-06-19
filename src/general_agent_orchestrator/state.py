from typing import Literal, Annotated 

from langgraph.graph import MessagesState 


def add_or_reset(left: list[str], right: list[str] | None) -> list[str]:
    if right is None:
        return []
    else:
        return left + right

def add_by_increment(old: list[tuple[int, str]], to_add: str) -> list[tuple[int,str]]:
    try:
        last_idx = old[-1][0]
    except IndexError:
        return [(0,to_add)]
    return old + [(last_idx + 1, to_add)]
    

class AgentState(MessagesState):
    ask_tool_permission: Literal['y','n']
    parallel_tool_calls: bool
    research_results: Annotated[list[str], add_or_reset]  # Accumulated across N branches by send then deleted in compilation node.
    query: str # Consumed by each research agent
    compiled_results: Annotated[list[str], add_by_increment]
    

    
