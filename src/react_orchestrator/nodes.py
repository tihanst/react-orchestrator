# pyright: basic
import json
import operator
from functools import reduce
from typing import Any
from pathlib import Path
from datetime import datetime
import logging
import threading

from .state import AgentState
from .agent_tools import ALL_TOOLS, VIRTUAL_TOOLS_FAN_OUT

from langgraph.types import interrupt, Send 
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage, messages_to_dict
from langchain_core.runnables import RunnableConfig
from langchain_together import ChatTogether
from langgraph.graph import END

from tavily import TavilyClient

from .settings import settings

logger = logging.getLogger(__name__)

SETTINGS = settings

llm = ChatTogether(model=SETTINGS.llm_model, max_tokens=SETTINGS.llm_max_tokens).bind_tools(
    tools=ALL_TOOLS, 
    parallel_tool_calls=False if SETTINGS.parallel_tool_calls=='n' else True) 

research_llm = ChatTogether(model=SETTINGS.llm_model, max_tokens=SETTINGS.llm_max_tokens) 


_search_log_lock = threading.Lock()

def assistant(state: AgentState, config: RunnableConfig):

    logger.debug("entering assistant")

    accumulator = None
    ai_message_list =  []
    for chunk in llm.stream(state["messages"], config=config):

        ai_message_list.append(chunk)

        if accumulator:
            accumulator += chunk
        else:
            accumulator = chunk

    ai_message = AIMessage(**reduce(operator.add, ai_message_list).model_dump   (exclude={"type"})) 
    return {"messages": [ai_message]} 


# Conditional edge from assistant
def check_tool_or_end(state: AgentState):
    logger.debug("entering check_tool_or_end_state")

    last_msg = state["messages"][-1]

    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        print("exiting")
        return END 
    else:
        return "check_tool_permission"
    

def check_tool_permission(state: AgentState):
    logger.debug("entering check_tool_permission")
    
    last_msg = state["messages"][-1]
    assert(isinstance(last_msg, AIMessage))
    tool_chosen = last_msg.tool_calls[0] # Hard-coded assumption is no parallel tool calls possible
    if state["ask_tool_permission"] == 'y':

        tool_decision = interrupt(f"Call tool:\n{tool_chosen['name']}\nwith arguments: {', '.join([f'{x} = {y} ' for x,y in tool_chosen['args'].items()])}?\n(y/n)\n>")

        if tool_decision.strip().lower()[0] != 'y':
            # Provides a ToolMessage to messages state that tool use was denied, to be sent back with message history to assistant via after_check_tool_permission conditional edge
            tool_reject_message = ToolMessage(content=f"The user has denied the invocation of the tool {tool_chosen['name']}",
                                              tool_call_id = tool_chosen["id"])
            return {"messages": [tool_reject_message]}
        else:
            # Tool use approved, proceed to after_check_tool_permission conditional edge without altering messages state
            return {}
    
    else:
        return {}
        

def after_check_tool_permission(state: AgentState):
    logger.debug("entering after_check_tool_permission")
    msg = state["messages"][-1]
    
    if isinstance(msg, ToolMessage):
        # If last msg is a ToolMessage tool use was rejected and we go back to assistant
        return "assistant" 
    
    elif isinstance(msg, AIMessage) and msg.tool_calls[0]["name"] in {t.name for t in VIRTUAL_TOOLS_FAN_OUT}:
        # A call for the research agent fan-out pattern
        queries = msg.tool_calls[0]["args"]["queries"]
        return [Send("research_agent_node", {"query": q}) for q in queries]
    else:
    # Permission was given to go to use the tool
        return "tools"
             
            
def research_agent_node(state: AgentState):

    RESEARCH_SYSTEM = (
        f"You are an expert research information synthesis agent. You summarize/answer "
        "retrieved research information into the most suscinct text possible, but without "
        "any extreme terseness that would lose any points, facts, or key information from the "
        "provided text you are asked to summarize."
    )

    RESEARCH_PROMPT_START = (
        "The following text chunks have been retrieved via web search from the reserach query:\n " 
        f"{state["query"]}\n" 
        "Summarize the results, weighing importance by the relevancy score given, of the query (or provide an answer if the query is a question) "
        "with the retrieved results:\n\n"
    )

    client = TavilyClient(api_key=SETTINGS.websearch_api_key)

    resp = client.search(
        query=state["query"],
        search_depth='advanced',
        chunks_per_source=3,
        max_results=5,
        include_answer=True,
        include_raw_content=True,
        exclude_domains=['medium.com', 'linkedin.com', 'facebook.com'],
        include_usage=True   
    )

    with _search_log_lock: # Prevent race conditions if multiple large responses are in fan-out pattern
        with open(Path(SETTINGS.search_logs) / "search_logs.log", "a+") as f:
            try:

                final_payload: dict[str, Any] = {
                    "single_or_multiple":"multiple",
                    "time": datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),
                    "payload": resp 
            }
                f.write(json.dumps(final_payload)+'\n')
            except Exception as e:
                print(f"Problem json serializing with e as:\n{e}")

    content = "" 
    for result in enumerate(resp["results"]):
        content += (f"Result number {result[0]}, relevance score: {result[1]["score"]}\n"
                    f"{result[1]["content"]}\n\n"
                )
    
    RESEARCH_FINAL_PROMPT = RESEARCH_PROMPT_START + content
    
    messages = [
        SystemMessage(content=RESEARCH_SYSTEM),
        HumanMessage(content=RESEARCH_FINAL_PROMPT)
    ]

    analysis = research_llm.invoke(messages)

    return {"research_results": [analysis.content]}



def compile_research(state: AgentState):

    research = "\n\n\n".join(state["research_results"])

    ai_msg_tool_emmision = state["messages"][-1]
    
    try:
        assert isinstance(ai_msg_tool_emmision, AIMessage), f"compile_research node fail, last message:\n{ai_msg_tool_emmision}\n>Not an ai message tool call emission"
    except Exception as e:
        raise e
    
    tool_id = ai_msg_tool_emmision.tool_calls[0]["id"]

    tool_message = ToolMessage(content=research, tool_call_id=tool_id)
    return {
        "messages": [tool_message],
        "compiled_results": [research],
        "research_results": None # Reset field via custom reducer
        }

