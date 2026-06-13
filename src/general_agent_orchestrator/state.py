from typing import Literal 

from langgraph.graph import MessagesState 


class AgentState(MessagesState):
    ask_tool_permission: Literal['y','n']
    parallel_tool_calls: bool 


    
