
import sys
from datetime import datetime

from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from .graph import graph
from .state import AgentState
from .settings import Settings



SETTINGS = Settings()

DEFAULT_SYSTEM_MSG = ("You are a helpful general assistant who will answer the user's " 
        "queries. You have access to some tools you can use to answer queries. If the user asks you to use websearch to answer the query then "
        "utilize the Tavily websearch tool that you have access to and utilize the context "
        "that it returns. Ensure that you use it in the way a person would form a normal google query. "
        "Do not use short form phrases. Ask a full question that encapsulates the user's intent. " 
        "If you ever add your own context in addition to that which came from "
        "the websearch in order to answer, place it at the end of your response and "
        "indicate it with the tags <my_own>."
    )

def run_sub_agent(user_prompt: str, system_prompt:str, agent_name: str) -> str:


    ADDENDUM_SYSTEM_MSG = (
        "If the user asks you to use websearch to answer the query then "
        "utilize the Tavily websearch tool that you have access to and utilize the context "
        "that it returns. Ensure that you use it in the way a person would form a normal google query. "
        "Do not use short form phrases. Ask a full question that encapsulates the user's intent. " 
        "If you ever add your own context in addition to that which came from "
        "the websearch in order to answer, place it at the end of your response and "
        "indicate it with the tags <my_own>."

        f"Finally MAKE SURE to begin your response back to the user with {agent_name}: <Response goes here>"
)
    print(f"\nCalling {agent_name} agent\n")
    agent_state = AgentState(
        messages=[],
        ask_tool_permission=SETTINGS.ask_tool_permissions,
        parallel_tool_calls=False if SETTINGS.parallel_tool_calls=='n' else True
        )

    if not system_prompt:
        system_message = SystemMessage(content=DEFAULT_SYSTEM_MSG)
    else:
        system_message = SystemMessage(content=system_prompt + "\n\n" + ADDENDUM_SYSTEM_MSG)
    
    user_msg = HumanMessage(content=user_prompt)

    fin_agent_name = agent_name or "agent_"
    thread_id = f"{fin_agent_name}{datetime.now().strftime("%Y_%m_%D_%H_%M_%S")}"

    config: RunnableConfig = {
        "configurable": {
            "thread_id": thread_id,
        }
    }   
    
    message_packet = [system_message, user_msg]
    agent_state["messages"] = message_packet

    response = graph.invoke(agent_state, config=config)

    try:
        return response["messages"][-1].content
    except Exception as e:
        return f"Explain that we got an error and summarize the type and what went wrong: {e}"


# def run(user_prompt: str | None, system_prompt: str | None = None, agent_name: str | None = None) -> str:
def run() -> str:
    user_prompt= "What is the best architectural structure to use to build an agent eval harness?"  #"What happened during the first half day of trading price action for Spacex's stock that just had an IPO?"
    system_prompt="You are an excellent news lookup and synthesis agent."
    agent_name="Stupid_guy"

    ADDENDUM_SYSTEM_MSG = (
        "If the user asks you to use websearch to answer the query then "
        "utilize the Tavily websearch tool that you have access to and utilize the context "
        "that it returns. Ensure that you use it in the way a person would form a normal google query. "
        "Do not use short form phrases. Ask a full question that encapsulates the user's intent. " 
        "If you ever add your own context in addition to that which came from "
        "the websearch in order to answer, place it at the end of your response and "
        "indicate it with the tags <my_own>."

        f"Finally MAKE SURE to begin your response back to the user with {agent_name}: <Response goes here>"
)
    print(f"\nCalling {agent_name} agent\n")
    agent_state = AgentState(
        messages=[],
        ask_tool_permission=SETTINGS.ask_tool_permissions,
        parallel_tool_calls=False if SETTINGS.parallel_tool_calls=='n' else True
        )

    if not system_prompt:
        system_message = SystemMessage(content=DEFAULT_SYSTEM_MSG)
    else:
        system_message = SystemMessage(content=system_prompt + "\n\n" + ADDENDUM_SYSTEM_MSG)
    
    user_msg = HumanMessage(content=user_prompt)

    fin_agent_name = agent_name or "agent_"
    thread_id = f"{fin_agent_name}{datetime.now().strftime("%Y_%m_%D_%H_%M_%S")}"

    config: RunnableConfig = {
        "configurable": {
            "thread_id": thread_id,
        }
    }   
    
    message_packet = [system_message, user_msg]
    agent_state["messages"] = message_packet

    response = graph.invoke(agent_state, config=config)

    try:
        return response["messages"][-1].content
    except Exception as e:
        return f"Explain that we got an error and summarize the type and what went wrong: {e}"

def main(system_prompt: str | None = None, agent_name: str | None = None):

    if not system_prompt:
        system_message = SystemMessage(content=DEFAULT_SYSTEM_MSG)
    else:
        system_message = SystemMessage(content=system_prompt)

    fin_agent_name = agent_name or "agent_"
    thread_id = f"{fin_agent_name}{datetime.now().strftime("%Y_%m_%D_%H_%M_%S")}"

    config = {
    "thread_id": thread_id, 
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
                sys.exit(0)
            msgs: list[AnyMessage] = [system_message, HumanMessage(content=first_q)]
            agent_state["messages"] = msgs
            start_flag += 1
        else:
            follow_up_q = input("\nprompt> ").strip()
            if follow_up_q == "!exit":
                print("Ending...")
                sys.exit(0) 
            agent_state["messages"] += [HumanMessage(content=follow_up_q)]


        for chunk, metadata in graph.stream(agent_state, config={"configurable": config}, stream_mode="messages"):
            if metadata["langgraph_node"] == "assistant" and chunk.content:
                print(chunk.content, end="", flush=True)
            
        state = graph.get_state(config={"configurable": config})
        # What is this below
        if state.next and state.tasks and state.tasks[0].interrupts:
            interrupt_value = state.tasks[0].interrupts[0].value
            user_input = input(interrupt_value)
            for chunk, metadata in graph.stream(Command(resume=user_input), config={"configurable": config}, stream_mode="messages"):
                if metadata["langgraph_node"] == "assistant" and chunk.content:
                    print(chunk.content, end="", flush=True)


        #print(f"Checkpointer is:\n{graph.get_state(config={"configurable":config})}")

if __name__ == "__main__":

    # if not os.path.isfile('../../viz/graph_image.png'):
    #     graph.get_graph().draw_mermaid_png(output_file_path='./graph_image.png')

    print("Starting up...\n")

    ans =  run()
    print(f"Final answer:\n\n{ans}")
    

        
