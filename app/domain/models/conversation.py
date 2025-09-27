from typing import TypedDict


class ConversationState(TypedDict, total=False):
    user_id: str
    input_text: str
    output_text: str
