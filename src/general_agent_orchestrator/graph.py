from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.graph import END

from .nodes import assistant, check_tool_or_end, check_tool_permission, after_check_tool_permission, cleanup_before_quit
from .state import AgentState
from .agent_tools import tavily_search_tool, list_directory

builder = StateGraph(AgentState)

# Nodes
tools = ToolNode([tavily_search_tool, list_directory])
builder.add_node("assistant", assistant)
builder.add_node("check_tool_permission", check_tool_permission)
builder.add_node("tools", tools)
builder.add_node("cleanup_before_quit", cleanup_before_quit)


# Edges

builder.add_conditional_edges("assistant", check_tool_or_end, path_map={"cleanup_before_quit":"cleanup_before_quit", "check_tool_permission":"check_tool_permission"})
builder.add_conditional_edges("check_tool_permission", after_check_tool_permission, path_map={"assistant":"assistant", "tools":"tools"})
builder.add_edge("tools", "assistant")
builder.add_edge("cleanup_before_quit", END)


# Setup

builder.set_entry_point("assistant")
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)


