from app_transformers import demo as demo_transformers
from app_lumaai import demo as demo_lumaai
from app_allenai import demo as demo_allenai
from app_claude import demo as demo_claude
from app_cohere import demo as demo_cohere
from app_experimental import demo as demo_experimental
from app_fal import demo as demo_fal
from app_fireworks import demo as demo_fireworks
from app_huggingface import demo as demo_huggingface
from app_meta import demo as demo_meta
from app_mistral import demo as demo_mistral
from app_nvidia import demo as demo_nvidia
from app_omini import demo as demo_omini
from app_paligemma import demo as demo_paligemma
from app_perplexity import demo as demo_perplexity
from app_playai import demo as demo_playai
from app_replicate import demo as demo_replicate
from app_sambanova import demo as demo_sambanova
from app_showui import demo as demo_showui
from app_together import demo as demo_together
from app_xai import demo as demo_grok
from app_qwen import demo as demo_qwen
from app_deepseek import demo as demo_deepseek
from app_crew import demo as demo_crew
from app_compare import demo as demo_compare
from app_hyperbolic import demo as demo_hyperbolic
from app_openai import demo as demo_openai
from app_gemini_coder import demo as demo_gemini_coder
from app_gemini import demo as demo_gemini
from app_gemini_voice import demo as demo_gemini_voice
from app_hyperbolic_coder import demo as demo_hyperbolic_coder
from app_smolagents import demo as demo_smolagents
from app_groq import demo as demo_groq
from app_groq_coder import demo as demo_groq_coder
from app_openai_coder import demo as demo_openai_coder
from utils import get_app

# Create mapping of providers to their demos
PROVIDERS = {
    "Phi-4": demo_transformers,
    "OpenAI Coder": demo_openai_coder,
    "Gemini Coder": demo_gemini_coder,
    "OpenAI": demo_openai,
    "Gemini": demo_gemini,
    "Gemini Voice": demo_gemini_voice,
    "Groq Coder": demo_groq_coder,
    "Hyperbolic Coder": demo_hyperbolic_coder,
    "SmolAgents": demo_smolagents,
    "DeepSeek": demo_deepseek,
    "Compare": demo_compare,
    "Qwen" : demo_qwen,
    "Hyperbolic": demo_hyperbolic,
    "CrewAI": demo_crew,
    "LumaAI": demo_lumaai,
    "Grok": demo_grok,
    "Cohere": demo_cohere,
    "SambaNova": demo_sambanova,
    "OminiControl": demo_omini,
    "Fireworks": demo_fireworks,
    "Together": demo_together,
    "Groq": demo_groq,
    "Meta Llama": demo_meta,
    "Paligemma": demo_paligemma,
    "Replicate": demo_replicate,
    "Huggingface": demo_huggingface,
    "Fal": demo_fal,
    "ShowUI": demo_showui,
    "PlayAI": demo_playai,
    "Claude": demo_claude,
    "Allen AI": demo_allenai,
    "Perplexity": demo_perplexity,
    "Experimental": demo_experimental,
    "Mistral": demo_mistral,
    "NVIDIA": demo_nvidia,
}

demo = get_app(models=list(PROVIDERS.keys()), default_model="Phi-4", src=PROVIDERS, dropdown_label="Select Provider")

if __name__ == "__main__":
    demo.queue(api_open=False).launch(show_api=False)
