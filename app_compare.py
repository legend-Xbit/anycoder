import os

import google.generativeai as genai
import gradio as gr
import openai
from anthropic import Anthropic
from openai import OpenAI  # Add explicit OpenAI import


def get_all_models():
    """Get all available models from the registries."""
    return [
        "SambaNova: Meta-Llama-3.2-1B-Instruct",
        "SambaNova: Meta-Llama-3.2-3B-Instruct",
        "SambaNova: Llama-3.2-11B-Vision-Instruct",
        "SambaNova: Llama-3.2-90B-Vision-Instruct",
        "SambaNova: Meta-Llama-3.1-8B-Instruct",
        "SambaNova: Meta-Llama-3.1-70B-Instruct",
        "SambaNova: Meta-Llama-3.1-405B-Instruct",
        "Hyperbolic: Qwen/Qwen2.5-Coder-32B-Instruct",
        "Hyperbolic: meta-llama/Llama-3.2-3B-Instruct",
        "Hyperbolic: meta-llama/Meta-Llama-3.1-8B-Instruct",
        "Hyperbolic: meta-llama/Meta-Llama-3.1-70B-Instruct",
        "Hyperbolic: meta-llama/Meta-Llama-3-70B-Instruct",
        "Hyperbolic: NousResearch/Hermes-3-Llama-3.1-70B",
        "Hyperbolic: Qwen/Qwen2.5-72B-Instruct",
        "Hyperbolic: deepseek-ai/DeepSeek-V2.5",
        "Hyperbolic: meta-llama/Meta-Llama-3.1-405B-Instruct",
    ]


def generate_discussion_prompt(original_question: str, previous_responses: list[str]) -> str:
    """Generate a prompt for models to discuss and build upon previous
    responses.
    """
    prompt = f"""You are participating in a multi-AI discussion about this question: "{original_question}"

Previous responses from other AI models:
{chr(10).join(f"- {response}" for response in previous_responses)}

Please provide your perspective while:
1. Acknowledging key insights from previous responses
2. Adding any missing important points
3. Respectfully noting if you disagree with anything and explaining why
4. Building towards a complete answer

Keep your response focused and concise (max 3-4 paragraphs)."""
    return prompt


def generate_consensus_prompt(original_question: str, discussion_history: list[str]) -> str:
    """Generate a prompt for final consensus building."""
    return f"""Review this multi-AI discussion about: "{original_question}"

Discussion history:
{chr(10).join(discussion_history)}

As a final synthesizer, please:
1. Identify the key points where all models agreed
2. Explain how any disagreements were resolved
3. Present a clear, unified answer that represents our collective best understanding
4. Note any remaining uncertainties or caveats

Keep the final consensus concise but complete."""


def chat_with_openai(model: str, messages: list[dict], api_key: str | None) -> str:
    import openai

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content


def chat_with_anthropic(messages: list[dict], api_key: str | None) -> str:
    """Chat with Anthropic's Claude model."""
    client = Anthropic(api_key=api_key)
    response = client.messages.create(model="claude-3-sonnet-20240229", messages=messages, max_tokens=1024)
    return response.content[0].text


def chat_with_gemini(messages: list[dict], api_key: str | None) -> str:
    """Chat with Gemini Pro model."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")

    # Convert messages to Gemini format
    gemini_messages = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        gemini_messages.append({"role": role, "parts": [msg["content"]]})

    response = model.generate_content([m["parts"][0] for m in gemini_messages])
    return response.text


def chat_with_sambanova(
    messages: list[dict], api_key: str | None, model_name: str = "Llama-3.2-90B-Vision-Instruct"
) -> str:
    """Chat with SambaNova's models using their OpenAI-compatible API."""
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.sambanova.ai/v1",
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.1,
        top_p=0.1,  # Use the specific model name passed in
    )
    return response.choices[0].message.content


def chat_with_hyperbolic(
    messages: list[dict], api_key: str | None, model_name: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
) -> str:
    """Chat with Hyperbolic's models using their OpenAI-compatible API."""
    client = OpenAI(api_key=api_key, base_url="https://api.hyperbolic.xyz/v1")

    # Add system message to the start of the messages list
    full_messages = [
        {"role": "system", "content": "You are a helpful assistant. Be descriptive and clear."},
        *messages,
    ]

    response = client.chat.completions.create(
        model=model_name,  # Use the specific model name passed in
        messages=full_messages,
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def multi_model_consensus(
    question: str, selected_models: list[str], rounds: int = 3, progress: gr.Progress = gr.Progress()
) -> list[tuple[str, str]]:
    if not selected_models:
        raise gr.Error("Please select at least one model to chat with.")

    chat_history = []
    progress(0, desc="Getting responses from all models...")

    # Get responses from all models in parallel
    for i, model in enumerate(selected_models):
        provider, model_name = model.split(": ", 1)
        progress((i + 1) / len(selected_models), desc=f"Getting response from {model}...")

        try:
            if provider == "Anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                response = chat_with_anthropic(messages=[{"role": "user", "content": question}], api_key=api_key)
            elif provider == "SambaNova":
                api_key = os.getenv("SAMBANOVA_API_KEY")
                response = chat_with_sambanova(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": question},
                    ],
                    api_key=api_key,
                    model_name=model_name,
                )
            elif provider == "Hyperbolic":
                api_key = os.getenv("HYPERBOLIC_API_KEY")
                response = chat_with_hyperbolic(
                    messages=[{"role": "user", "content": question}],
                    api_key=api_key,
                    model_name=model_name,
                )
            else:  # Gemini
                api_key = os.getenv("GEMINI_API_KEY")
                response = chat_with_gemini(messages=[{"role": "user", "content": question}], api_key=api_key)

            chat_history.append((model, response))
        except Exception as e:
            chat_history.append((model, f"Error: {e!s}"))

    progress(1.0, desc="Done!")
    return chat_history


with gr.Blocks() as demo:
    gr.Markdown("# Model Response Comparison")
    gr.Markdown("""Select multiple models to compare their responses""")

    with gr.Row():
        with gr.Column():
            model_selector = gr.Dropdown(
                choices=get_all_models(),
                multiselect=True,
                label="Select Models",
                info="Choose models to compare",
                value=["SambaNova: Llama-3.2-90B-Vision-Instruct", "Hyperbolic: Qwen/Qwen2.5-Coder-32B-Instruct"],
            )

    chatbot = gr.Chatbot(height=600, label="Model Responses")
    msg = gr.Textbox(label="Prompt", placeholder="Ask a question to compare model responses...")

    def respond(message, selected_models):
        chat_history = multi_model_consensus(message, selected_models, rounds=1)
        return chat_history

    msg.submit(respond, [msg, model_selector], [chatbot])

for fn in demo.fns.values():
    fn.api_name = False

if __name__ == "__main__":
    demo.launch()
