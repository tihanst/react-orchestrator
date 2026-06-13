# pyright: basic
import json
import operator
from functools import reduce
from pathlib import Path
from datetime import datetime

from .state import AgentState
from .agent_tools import tavily_search_tool, list_directory

from langgraph.types import interrupt
from langchain_together import ChatTogether
from langchain_core.messages import AIMessage, ToolMessage, messages_to_dict
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END

from .settings import Settings

SETTINGS = Settings()

llm = ChatTogether(model=SETTINGS.llm_model).bind_tools(
    tools=[tavily_search_tool, list_directory], 
    parallel_tool_calls=False if SETTINGS.parallel_tool_calls=='n' else True) 


def assistant(state: AgentState, config: RunnableConfig):

    print("\nentering assistant")

    accumulator = None
    ai_message_list =  []
    for chunk in llm.stream(state["messages"], config=config):
        # print(f"----\n{repr(chunk)}\n----")

        ai_message_list.append(chunk)

        if accumulator:
            accumulator += chunk
        else:
            accumulator = chunk

        # For streaming content: Not used as printing is done at graph level   
        # if not chunk.tool_call_chunks and chunk.content:
        #     print(chunk.content, end="", flush=True)

    ai_message = AIMessage(**reduce(operator.add, ai_message_list).model_dump   (exclude={"type"})) 
    return {"messages": [ai_message]} 

#conditional edge from assistant
def check_tool_or_end(state: AgentState):
    print("\nentering check_tool_or_end_state")

    last_msg = state["messages"][-1]

    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        print("exiting")
        return "cleanup_before_quit" 
    else:
        return "check_tool_permission"
    

def check_tool_permission(state: AgentState):
    print("\nentering check_tool_permission")
    
    last_msg = state["messages"][-1]
    assert(isinstance(last_msg, AIMessage))
    tool_chosen = last_msg.tool_calls[0]
    if state["ask_tool_permission"] == 'y':

        tool_decision = interrupt(f"Call tool {tool_chosen['name']} with arguments: {', '.join([f'{x} = {y} ' for x,y in tool_chosen['args'].items()])}?\n(y/n)\n>")


        if tool_decision.strip().lower()[0] != 'y':
            # provides a ToolMessage to messages state that tool use was denied, to be sent back with message history to assistant via after_check_tool_permission conditional edge
            tool_reject_message = ToolMessage(content=f"The user has denied the invocation of the tool {tool_chosen['name']}",
                                              tool_call_id = tool_chosen["id"])
            return {"messages": [tool_reject_message]}
        else:
            # Tool use approved, proceed to after_check_tool_permission conditional edge without altering messages state
            return {}
        

def after_check_tool_permission(state: AgentState):
    print("\nentering after_check_tool_permission")
    msg = state["messages"][-1]
    
    if isinstance(msg, ToolMessage):
        # If last msg is a ToolMessage it was a rejection and we go back to assistant
        return "assistant" 
    else:
    # Permission was given to go to use the tool
        return "tools"
             
            
def cleanup_before_quit(state: AgentState):

    with open(Path(SETTINGS.agent_response_logs) / "response_history.jsonl", 'a', encoding='utf-8') as f:
              
              dat = messages_to_dict(state["messages"])
              time = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")

              package = {
                  "time":time,
                  "agent_run":dat
              }

              f.write(json.dumps(package) + "\n")
    return