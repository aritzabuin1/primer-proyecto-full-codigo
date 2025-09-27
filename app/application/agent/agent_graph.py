from langgraph.graph import END, StateGraph

from app.domain.models.conversation import ConversationState
from app.domain.ports.llm import LLMPort


def build_graph(llm: LLMPort):
    def reason(state: ConversationState) -> ConversationState:
        user_text = state.get("input_text", "")
        messages = [
            {"role": "system", "content": "Eres un asistente breve y directo."},
            {"role": "user", "content": user_text},
        ]
        reply = llm.chat(messages)
        state["output_text"] = reply
        return state

    graph = StateGraph(ConversationState)
    graph.add_node("reason", reason)
    graph.set_entry_point("reason")
    graph.add_edge("reason", END)
    return graph.compile()
