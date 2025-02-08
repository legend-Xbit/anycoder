from app_lumaai import demo as demo_lumaai
from app_claude import demo as demo_claude
from app_cohere import demo as demo_cohere
from app_fal import demo as demo_fal
from app_fireworks import demo as demo_fireworks
from app_meta import demo as demo_meta
from app_perplexity import demo as demo_perplexity
from app_playai import demo as demo_playai
from app_replicate import demo as demo_replicate
from app_sambanova import demo as demo_sambanova
from app_together import demo as demo_together
from app_xai import demo as demo_grok
from app_crew import demo as demo_crew
from app_hyperbolic import demo as demo_hyperbolic
from app_gemini_coder import demo as demo_gemini_coder
from app_gemini import demo as demo_gemini
from app_hyperbolic_coder import demo as demo_hyperbolic_coder
from app_smolagents import demo as demo_smolagents
from app_groq import demo as demo_groq
from app_groq_coder import demo as demo_groq_coder
from app_openai_coder import demo as demo_openai_coder
from app_langchain import demo as demo_langchain
from app_mistral import demo as demo_mistral
from app_minimax import demo as demo_minimax
from app_minimax_coder import demo as demo_minimax_coder
from app_nvidia import demo as demo_nvidia
from app_deepseek import demo as demo_deepseek
from app_qwen import demo as demo_qwen
from app_qwen_coder import demo as demo_qwen_coder
from app_nvidia_coder import demo as demo_nvidia_coder
from app_openai import demo as demo_openai
from utils import get_app

# Create mapping of providers to their demos
PROVIDERS = {
    "OpenAI Coder": demo_openai_coder,
    "Gemini Coder": demo_gemini_coder,
    "OpenAI": demo_openai,
    "NVIDIA Coder": demo_nvidia_coder,
    "Hyperbolic Coder": demo_hyperbolic_coder,
    "Hyperbolic": demo_hyperbolic,
    "Groq Coder": demo_groq_coder,
    "Qwen Coder": demo_qwen_coder,
    "Qwen": demo_qwen,
    "DeepSeek Coder": demo_deepseek,
    "Minimax Coder": demo_minimax_coder,
    "NVIDIA": demo_nvidia,
    "Minimax": demo_minimax,
    "Mistral": demo_mistral,
    "Langchain Agent": demo_langchain,
    "Gemini": demo_gemini,
    "SmolAgents": demo_smolagents,
    "CrewAI": demo_crew,
    "LumaAI": demo_lumaai,
    "Grok": demo_grok,
    "Cohere": demo_cohere,
    "SambaNova": demo_sambanova,
    "Fireworks": demo_fireworks,
    "Together": demo_together,
    "Groq": demo_groq,
    "Meta Llama": demo_meta,
    "Replicate": demo_replicate,
    "Fal": demo_fal,
    "PlayAI": demo_playai,
    "Claude": demo_claude,
    "Perplexity": demo_perplexity,
}

demo = get_app(
    models=list(PROVIDERS.keys()),
    default_model="OpenAI Coder",
    src=PROVIDERS,
    dropdown_label="Select Provider",
)

if __name__ == "__main__":
    demo.queue(api_open=False).launch(show_api=False)
