from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt.tool_node import ToolNode
from langgraph.graph import END

from .nodes import (
    assistant, 
    check_tool_or_end, 
    check_tool_permission, 
    after_check_tool_permission, 
    research_agent_node, 
    compile_research
)

from .state import AgentState
from .agent_tools import TOOL_NODE_ROUTED_TOOLS 


builder = StateGraph(AgentState)

# Nodes
tools = ToolNode(TOOL_NODE_ROUTED_TOOLS)
builder.add_node("assistant", assistant)
builder.add_node("check_tool_permission", check_tool_permission)
builder.add_node("research_agent_node", research_agent_node)
builder.add_node('compile_research', compile_research)
builder.add_node("tools", tools)


# Edges
builder.add_conditional_edges("assistant", check_tool_or_end, path_map={END:END, "check_tool_permission":"check_tool_permission"})
builder.add_conditional_edges("check_tool_permission", after_check_tool_permission, path_map={"assistant":"assistant", "tools":"tools"})
builder.add_edge("research_agent_node", "compile_research")
builder.add_edge("compile_research", "assistant")
builder.add_edge("tools", "assistant")


# Setup

builder.set_entry_point("assistant")
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)


