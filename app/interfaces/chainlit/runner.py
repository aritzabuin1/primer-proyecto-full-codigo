import chainlit as cl
from app.application.agent.agent_graph import build_graph
from app.infrastructure.llm.groq_client import GroqLLM

# wiring(inyección): creamos el adapter y lo pasamos al grafo (Application)
LLM = GroqLLM()
GRAPH = build_graph(LLM)


@cl.on_chat_start
async def start():
    await cl.Message(content="¡Hola! Envía un texto y te respondo.").send()


@cl.on_message
async def on_message(message: cl.Message):
    user_text = message.content or ""
    result = GRAPH.invoke({"input_text": user_text})
    reply = result.get("output_text", "")
    await cl.Message(content=reply).send()
