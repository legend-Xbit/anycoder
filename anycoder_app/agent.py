"""
Agent functionality for interactive code generation with follow-up questions and task planning.
"""
import os
from typing import Dict, List, Optional, Tuple, Generator
import gradio as gr

from .models import (
    get_inference_client, get_real_model_id, history_to_messages,
    history_to_chatbot_messages, strip_thinking_tags
)
from .deploy import generation_code


def agent_generate_with_questions(
    query: Optional[str],
    setting: Dict[str, str],
    history: List,
    current_model: Dict,
    language: str,
    provider: str,
    profile: Optional[gr.OAuthProfile] = None,
    token: Optional[gr.OAuthToken] = None,
    max_questions: int = 3
) -> Generator[Tuple[List, List], None, None]:
    """
    Agent that asks follow-up questions, creates a task list, and generates code.
    
    Args:
        query: Initial user request
        setting: System settings
        history: Conversation history
        current_model: Selected model configuration
        language: Target programming language/framework
        provider: Model provider
        profile: User OAuth profile
        token: User OAuth token
        max_questions: Maximum number of follow-up questions to ask
        
    Yields:
        Tuples of (history, chatbot_messages) at each step
    """
    if not query or not query.strip():
        return
    
    # Initialize history with user's initial query
    current_history = history + [[query, ""]]
    
    # Step 1: Agent analyzes the request and asks follow-up questions
    agent_system_prompt = """You are a helpful coding assistant that helps users clarify their requirements before generating code.

Your task is to:
1. Analyze the user's request
2. Ask 1-3 clarifying questions to better understand their needs
3. Focus on important details like:
   - Target audience and use case
   - Specific features or functionality needed
   - Design preferences (colors, layout, style)
   - Data sources or APIs to integrate
   - Performance or scalability requirements

Output ONLY the questions, numbered 1, 2, 3, etc. Keep questions concise and focused.
Do not generate code yet - just ask the questions."""

    # Get LLM client
    client = get_inference_client(current_model.get('model_id', 'Qwen/Qwen2.5-Coder-32B-Instruct'), provider)
    model_id = get_real_model_id(current_model.get('model_id', 'Qwen/Qwen2.5-Coder-32B-Instruct'))
    
    # Prepare messages for follow-up questions
    messages = [
        {'role': 'system', 'content': agent_system_prompt},
        {'role': 'user', 'content': f"User wants to create: {query}\n\nLanguage/Framework: {language}\n\nAsk clarifying questions."}
    ]
    
    # Generate follow-up questions
    questions_response = ""
    try:
        # Try to use the client (works for both InferenceClient and OpenAI-compatible clients)
        stream = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            stream=True
        )
        for chunk in stream:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                questions_response += chunk.choices[0].delta.content
                # Update display in real-time
                temp_history = current_history[:-1] + [[query, f"🤔 **Analyzing your request...**\n\n{questions_response}"]]
                yield (temp_history, history_to_chatbot_messages(temp_history))
    except Exception as e:
        error_msg = f"❌ Error asking follow-up questions: {str(e)}"
        temp_history = current_history[:-1] + [[query, error_msg]]
        yield (temp_history, history_to_chatbot_messages(temp_history))
        return
    
    # Update history with agent's questions
    current_history[-1][1] = f"🤔 **Let me ask you a few questions to better understand your needs:**\n\n{questions_response}\n\n💬 Please answer these questions in your next message."
    yield (current_history, history_to_chatbot_messages(current_history))
    
    # Wait for user response (this will be handled by the UI)
    # For now, we'll return and let the user respond, then continue in the next call
    return


def agent_process_answers_and_generate(
    user_answers: str,
    original_query: str,
    questions: str,
    setting: Dict[str, str],
    history: List,
    current_model: Dict,
    language: str,
    provider: str,
    profile: Optional[gr.OAuthProfile] = None,
    token: Optional[gr.OAuthToken] = None,
    code_output=None,
    history_output=None,
    history_state=None
) -> Generator:
    """
    Process user's answers, create task list, and generate code.
    
    Args:
        user_answers: User's responses to the questions
        original_query: Original user request
        questions: Agent's questions
        setting: System settings
        history: Conversation history
        current_model: Selected model configuration
        language: Target programming language/framework
        provider: Model provider
        profile: User OAuth profile
        token: User OAuth token
        code_output: Code output component
        history_output: History output component
        history_state: History state
        
    Yields:
        Updates to code output and history
    """
    # Step 2: Create task list based on answers
    task_planning_prompt = f"""Based on the user's request and their answers, create a detailed task list for implementing the solution.

Original Request: {original_query}

Questions Asked:
{questions}

User's Answers:
{user_answers}

Create a numbered task list with 5-8 specific, actionable tasks. Each task should be clear and focused.
Start with "📋 **Task List:**" and then list the tasks."""

    client = get_inference_client(current_model.get('model_id', 'Qwen/Qwen2.5-Coder-32B-Instruct'), provider)
    model_id = get_real_model_id(current_model.get('model_id', 'Qwen/Qwen2.5-Coder-32B-Instruct'))
    
    messages = [
        {'role': 'system', 'content': 'You are a helpful coding assistant creating a task plan.'},
        {'role': 'user', 'content': task_planning_prompt}
    ]
    
    # Generate task list
    task_list = ""
    try:
        stream = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
            stream=True
        )
        for chunk in stream:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                task_list += chunk.choices[0].delta.content
                # Update display
                temp_history = history + [[user_answers, f"📋 **Creating task list...**\n\n{task_list}"]]
                yield {
                    history_state: temp_history,
                    history_output: history_to_chatbot_messages(temp_history)
                }
    except Exception as e:
        error_msg = f"❌ Error creating task list: {str(e)}"
        temp_history = history + [[user_answers, error_msg]]
        yield {
            history_state: temp_history,
            history_output: history_to_chatbot_messages(temp_history)
        }
        return
    
    # Update history with task list
    updated_history = history + [[user_answers, task_list]]
    yield {
        history_state: updated_history,
        history_output: history_to_chatbot_messages(updated_history)
    }
    
    # Step 3: Generate code based on refined requirements
    refined_query = f"""{original_query}

Additional Requirements (based on follow-up):
{user_answers}

Task List:
{task_list}

Please implement the above requirements following the task list."""
    
    # Add a message indicating code generation is starting
    code_gen_start_history = updated_history + [["[System]", "🚀 **Starting code generation based on your requirements...**"]]
    yield {
        history_state: code_gen_start_history,
        history_output: history_to_chatbot_messages(code_gen_start_history)
    }
    
    # Use the existing generation_code function for actual code generation
    # We need to pass the refined query and updated history
    for result in generation_code(
        refined_query,
        setting,
        updated_history,
        current_model,
        language,
        provider,
        profile,
        token,
        code_output,
        history_output,
        history_state
    ):
        yield result

