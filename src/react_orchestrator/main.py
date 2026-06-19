
import subprocess
import os
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import logging

from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, messages_to_dict
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, StateSnapshot

from . import agent_logger
from .graph import graph
from .state import AgentState
from .settings import settings 

logger = logging.getLogger(__name__)

SETTINGS = settings

DEFAULT_SYSTEM_MSG = ("You are a helpful general assistant who will answer the user's " 
        "queries. You have access to tools you can use to answer queries. If the user "
        "asks you to use websearch or internet search to gather information or research to answer the query, "
        "utilize the internet_research tool or parallel_internet_research_agent tool (if you need to make " 
        "multiple simultaneous related but non-overlapping queries) that you have access to, in order to retrieve relevant context. "
        "Ensure that you query this tool in the way a person would form a normal google search query. "
        "Do not use short form phrases. Ask a full question that encapsulates the user's intent. " 
        "If you ever add your own context in addition to that which came from "
        "the internet research in order to answer, place it at the end of your response and "
        "indicate it with the tags <my_own>."
    )

def cleanup_before_quit(state: StateSnapshot):

    with open(Path(SETTINGS.agent_response_logs) / "response_history.jsonl", 'a', encoding='utf-8') as f:
              
              messages: list[dict[str, str]] = messages_to_dict(state.values.get("messages", []))
              time = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")

              package: dict[Any, Any] = {
                  "time":time,
                  "agent_run": messages
              }

              f.write(json.dumps(package) + "\n")
    return


def main(system_prompt: str | None = None, agent_name: str | None = None):

    if not os.path.isfile('./docs/agent_graph.png'):
        print(os.getcwd())
        subprocess.run(["uv","run", "python", "utils/draw_correct_flow.py"])
        print("Saved agent_graph.png to /docs")

    print("Starting up...\n")

    if not system_prompt:
        system_message = SystemMessage(content=DEFAULT_SYSTEM_MSG)
    else:
        system_message = SystemMessage(content=system_prompt)

    fin_agent_name = agent_name or "agent_"
    thread_id = f"{fin_agent_name}{datetime.now().strftime("%Y_%m_%D_%H_%M_%S")}"

    config: RunnableConfig = {
        "configurable": {
            "thread_id": thread_id, 
        }
    }
    

    agent_state = AgentState(
        messages=[],
        ask_tool_permission=SETTINGS.ask_tool_permissions,
        parallel_tool_calls=False if SETTINGS.parallel_tool_calls=='n' else True
        )

    start_flag = 0 


    while True:
        
        if start_flag == 0:
            first_q = input("\nprompt> ").strip()
            if first_q == "!exit":
                print("\nEnding...\n")
                break
            msgs: list[AnyMessage] = [system_message, HumanMessage(content=first_q)]
            agent_state["messages"] = msgs
            start_flag += 1
        else:
            follow_up_q = input("\nprompt> ").strip()
            if follow_up_q == "!exit":
                print("Ending...")
                break
            agent_state["messages"] += [HumanMessage(content=follow_up_q)]


        for chunk, metadata in graph.stream(agent_state, config=config, stream_mode="messages"):
            if metadata["langgraph_node"] == "assistant" and chunk.content:
                print(chunk.content, end="", flush=True)


        while True: # Multiple tool permissions possible but parallel tool calls always disabled
            state = graph.get_state(config=config)
            
            if state.next and state.tasks and state.tasks[0].interrupts:
                interrupt_value = state.tasks[0].interrupts[0].value
                user_input = input(interrupt_value)
                for chunk, metadata in graph.stream(Command(resume=user_input), config=config, stream_mode="messages"):
                    if metadata["langgraph_node"] == "assistant" and chunk.content:
                        print(chunk.content, end="", flush=True)
            else:
                break # No further permission interrupts left

    final_state = graph.get_state(config=config)

    logger.info("Cleaning up before quitting.")
    cleanup_before_quit(final_state)


if __name__ == "__main__":

    print("Starting up...\n")

    ans =  main()
    print(f"Final answer:\n\n{ans}")
    

        
