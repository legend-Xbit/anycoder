"""
Project Importer - Standalone module for importing projects from various sources

This module provides functionality to import projects from:
- HuggingFace Spaces
- HuggingFace Models
- GitHub Repositories

No Gradio dependency required - pure Python implementation.
"""

import os
import re
import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from huggingface_hub import HfApi, list_repo_files


class ProjectImporter:
    """Main class for importing projects from various sources"""
    
    def __init__(self, hf_token: Optional[str] = None):
        """
        Initialize the ProjectImporter.
        
        Args:
            hf_token: Optional HuggingFace token for authenticated requests
        """
        self.hf_token = hf_token or os.environ.get("HF_TOKEN")
        self.api = HfApi(token=self.hf_token)
    
    def import_from_url(self, url: str) -> Dict[str, any]:
        """
        Import a project from any supported URL.
        
        Args:
            url: URL to import from (HF Space, HF Model, or GitHub)
        
        Returns:
            Dictionary containing:
            - status: Success/error message
            - code: Extracted code content
            - language: Detected language/framework
            - url: Original URL
            - metadata: Additional metadata
        """
        if not url or not url.strip():
            return {
                "status": "error",
                "message": "Please provide a valid URL",
                "code": "",
                "language": "unknown",
                "url": url,
                "metadata": {}
            }
        
        # Parse URL to determine source type
        kind, meta = self._parse_url(url)
        
        if kind == "hf_space":
            return self.import_space(meta["username"], meta["project"])
        elif kind == "hf_model":
            return self.import_model(meta["repo_id"])
        elif kind == "github":
            return self.import_github_repo(meta["owner"], meta["repo"])
        else:
            return {
                "status": "error",
                "message": "Unsupported URL format. Supported: HF Spaces, HF Models, GitHub repos",
                "code": "",
                "language": "unknown",
                "url": url,
                "metadata": {}
            }
    
    def import_space(self, username: str, project_name: str) -> Dict[str, any]:
        """
        Import a HuggingFace Space.
        
        Args:
            username: HuggingFace username
            project_name: Space name
        
        Returns:
            Dictionary with imported project data
        """
        try:
            space_id = f"{username}/{project_name}"
            space_info = self.api.space_info(space_id)
            
            # Detect if this is a transformers.js space
            if space_info.sdk == "static" and self._is_transformers_js_space(username, project_name):
                code, files = self._fetch_transformers_js_files(username, project_name)
                return {
                    "status": "success",
                    "message": f"Successfully imported transformers.js space: {space_id}",
                    "code": code,
                    "language": "transformers.js",
                    "url": f"https://huggingface.co/spaces/{space_id}",
                    "metadata": {
                        "sdk": "static",
                        "type": "transformers.js",
                        "files": files
                    }
                }
            
            # Handle multi-file spaces
            files = self._fetch_all_space_files(username, project_name, space_info.sdk)
            
            if files:
                code = self._format_multi_file_content(files, username, project_name, space_info.sdk)
                language = self._detect_language_from_sdk(space_info.sdk, files)  # Pass files for detection
                
                return {
                    "status": "success",
                    "message": f"Successfully imported space: {space_id}",
                    "code": code,
                    "language": language,
                    "url": f"https://huggingface.co/spaces/{space_id}",
                    "metadata": {
                        "sdk": space_info.sdk,
                        "files": list(files.keys())
                    }
                }
            else:
                # Fallback to single file
                main_file, content = self._fetch_main_file(username, project_name, space_info.sdk)
                
                if content:
                    return {
                        "status": "success",
                        "message": f"Successfully imported space: {space_id}",
                        "code": content,
                        "language": self._detect_language_from_sdk(space_info.sdk),
                        "url": f"https://huggingface.co/spaces/{space_id}",
                        "metadata": {
                            "sdk": space_info.sdk,
                            "main_file": main_file
                        }
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Could not find main file in space {space_id}",
                        "code": "",
                        "language": "unknown",
                        "url": f"https://huggingface.co/spaces/{space_id}",
                        "metadata": {"sdk": space_info.sdk}
                    }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to import space: {str(e)}",
                "code": "",
                "language": "unknown",
                "url": f"https://huggingface.co/spaces/{username}/{project_name}",
                "metadata": {}
            }
    
    def import_model(self, model_id: str, prefer_local: bool = False) -> Dict[str, any]:
        """
        Import a HuggingFace Model.
        
        Args:
            model_id: HuggingFace model ID (e.g., "meta-llama/Llama-2-7b")
            prefer_local: If True, prefer local inference code over serverless
        
        Returns:
            Dictionary with imported model data
        """
        try:
            # Get model info
            model_info = self.api.model_info(model_id)
            pipeline_tag = getattr(model_info, "pipeline_tag", None)
            library_name = getattr(model_info, "library_name", None)
            tags = getattr(model_info, "tags", [])
            
            # Check if this is an ONNX model (especially from onnx-community)
            is_onnx_model = (
                "onnx" in model_id.lower() or 
                "onnx" in str(library_name).lower() or
                any("onnx" in str(tag).lower() for tag in tags) or
                "transformers.js" in str(library_name).lower() or
                any("transformers.js" in str(tag).lower() for tag in tags)
            )
            
            # For ONNX models, try to extract Transformers.js code from README first
            if is_onnx_model:
                try:
                    readme = self._fetch_hf_model_readme(model_id)
                    if readme:
                        transformersjs_code = self._extract_transformersjs_code(readme, model_id)
                        if transformersjs_code:
                            return {
                                "status": "success",
                                "message": f"Successfully imported ONNX model: {model_id} (Transformers.js code)",
                                "code": transformersjs_code,
                                "language": "transformers.js",
                                "url": f"https://huggingface.co/{model_id}",
                                "metadata": {
                                    "pipeline_tag": pipeline_tag,
                                    "library_name": library_name,
                                    "code_type": "transformers.js",
                                    "is_onnx": True
                                }
                            }
                except Exception as e:
                    print(f"Failed to extract Transformers.js code: {e}")
            
            # Try to get inference provider code
            inference_code = self._generate_inference_code(model_id, pipeline_tag)
            
            # Try to get transformers/diffusers code from README
            readme_code = None
            try:
                readme = self._fetch_hf_model_readme(model_id)
                if readme:
                    _, readme_code = self._extract_code_from_markdown(readme)
            except:
                pass
            
            # Determine which code to return
            if inference_code and readme_code:
                code = readme_code if prefer_local else inference_code
                code_type = "local" if prefer_local else "inference"
                
                return {
                    "status": "success",
                    "message": f"Successfully imported model: {model_id} ({code_type} code)",
                    "code": code,
                    "language": "python",
                    "url": f"https://huggingface.co/{model_id}",
                    "metadata": {
                        "pipeline_tag": pipeline_tag,
                        "code_type": code_type,
                        "has_alternatives": True,
                        "inference_code": inference_code,
                        "local_code": readme_code
                    }
                }
            elif inference_code:
                return {
                    "status": "success",
                    "message": f"Successfully imported model: {model_id} (inference code)",
                    "code": inference_code,
                    "language": "python",
                    "url": f"https://huggingface.co/{model_id}",
                    "metadata": {
                        "pipeline_tag": pipeline_tag,
                        "code_type": "inference"
                    }
                }
            elif readme_code:
                return {
                    "status": "success",
                    "message": f"Successfully imported model: {model_id} (local code)",
                    "code": readme_code,
                    "language": "python",
                    "url": f"https://huggingface.co/{model_id}",
                    "metadata": {
                        "pipeline_tag": pipeline_tag,
                        "code_type": "local"
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"No code found for model: {model_id}",
                    "code": "",
                    "language": "python",
                    "url": f"https://huggingface.co/{model_id}",
                    "metadata": {"pipeline_tag": pipeline_tag}
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to import model: {str(e)}",
                "code": "",
                "language": "python",
                "url": f"https://huggingface.co/{model_id}",
                "metadata": {}
            }
    
    def import_github_repo(self, owner: str, repo: str) -> Dict[str, any]:
        """
        Import a GitHub repository.
        
        Args:
            owner: GitHub username/organization
            repo: Repository name
        
        Returns:
            Dictionary with imported repository data
        """
        try:
            readme = self._fetch_github_readme(owner, repo)
            
            if not readme:
                return {
                    "status": "error",
                    "message": f"Could not fetch README from {owner}/{repo}",
                    "code": "",
                    "language": "python",
                    "url": f"https://github.com/{owner}/{repo}",
                    "metadata": {}
                }
            
            lang, code = self._extract_code_from_markdown(readme)
            
            if code:
                return {
                    "status": "success",
                    "message": f"Successfully imported code from {owner}/{repo}",
                    "code": code,
                    "language": lang or "python",
                    "url": f"https://github.com/{owner}/{repo}",
                    "metadata": {
                        "source": "github",
                        "detected_language": lang
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"No relevant code found in README of {owner}/{repo}",
                    "code": "",
                    "language": "python",
                    "url": f"https://github.com/{owner}/{repo}",
                    "metadata": {}
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to import repository: {str(e)}",
                "code": "",
                "language": "python",
                "url": f"https://github.com/{owner}/{repo}",
                "metadata": {}
            }
    
    # ==================== Private Helper Methods ====================
    
    def _parse_url(self, url: str) -> Tuple[str, Optional[Dict]]:
        """Parse URL and detect source type"""
        try:
            parsed = urlparse(url.strip())
            netloc = (parsed.netloc or "").lower()
            path = (parsed.path or "").strip("/")
            
            # HuggingFace Spaces
            if ("huggingface.co" in netloc or "hf.co" in netloc) and path.startswith("spaces/"):
                parts = path.split("/")
                if len(parts) >= 3:
                    return "hf_space", {"username": parts[1], "project": parts[2]}
            
            # HuggingFace Model
            if ("huggingface.co" in netloc or "hf.co" in netloc) and not path.startswith(("spaces/", "datasets/")):
                parts = path.split("/")
                if len(parts) >= 2:
                    return "hf_model", {"repo_id": f"{parts[0]}/{parts[1]}"}
            
            # GitHub Repository
            if "github.com" in netloc:
                parts = path.split("/")
                if len(parts) >= 2:
                    return "github", {"owner": parts[0], "repo": parts[1]}
        
        except Exception:
            pass
        
        return "unknown", None
    
    def _is_transformers_js_space(self, username: str, project_name: str) -> bool:
        """Check if space is a transformers.js app"""
        try:
            files = list_repo_files(
                repo_id=f"{username}/{project_name}",
                repo_type="space",
                token=self.hf_token
            )
            
            has_html = any('index.html' in f for f in files)
            has_js = any('index.js' in f for f in files)
            has_css = any('style.css' in f for f in files)
            
            return has_html and has_js and has_css
        except:
            return False
    
    def _fetch_transformers_js_files(self, username: str, project_name: str) -> Tuple[str, Dict]:
        """Fetch transformers.js files and combine them"""
        files = {}
        file_names = ['index.html', 'index.js', 'style.css']
        
        for file_name in file_names:
            try:
                content_path = self.api.hf_hub_download(
                    repo_id=f"{username}/{project_name}",
                    filename=file_name,
                    repo_type="space"
                )
                with open(content_path, 'r', encoding='utf-8') as f:
                    files[file_name] = f.read()
            except:
                files[file_name] = ""
        
        # Combine files
        combined = f"""=== index.html ===
{files.get('index.html', '')}

=== index.js ===
{files.get('index.js', '')}

=== style.css ===
{files.get('style.css', '')}"""
        
        return combined, files
    
    def _fetch_all_space_files(self, username: str, project_name: str, sdk: str) -> Optional[Dict[str, str]]:
        """Fetch all relevant files from a space"""
        try:
            space_id = f"{username}/{project_name}"
            files = list_repo_files(repo_id=space_id, repo_type="space", token=self.hf_token)
            
            # Define file extensions to include
            include_extensions = {
                '.py', '.js', '.html', '.css', '.json', '.txt', '.yml', '.yaml',
                '.toml', '.cfg', '.ini', '.sh', '.md'
            }
            
            # Filter files
            relevant_files = [
                f for f in files
                if any(f.endswith(ext) for ext in include_extensions)
                and not f.startswith('.')
                and not f.startswith('__pycache__')
            ]
            
            # Limit number of files
            if len(relevant_files) > 50:
                relevant_files = relevant_files[:50]
            
            # Fetch file contents
            file_contents = {}
            for file in relevant_files:
                try:
                    file_path = self.api.hf_hub_download(
                        repo_id=space_id,
                        filename=file,
                        repo_type="space"
                    )
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_contents[file] = f.read()
                except:
                    continue
            
            return file_contents if file_contents else None
        
        except:
            return None
    
    def _format_multi_file_content(self, files: Dict[str, str], username: str, project_name: str, sdk: str) -> str:
        """Format multi-file content"""
        header = f"""IMPORTED PROJECT FROM HUGGING FACE SPACE
==============================================

Space: {username}/{project_name}
SDK: {sdk}
Files: {len(files)}

"""
        
        file_sections = []
        for filename, content in files.items():
            file_sections.append(f"=== {filename} ===\n{content}")
        
        return header + "\n\n".join(file_sections)
    
    def _fetch_main_file(self, username: str, project_name: str, sdk: str) -> Tuple[Optional[str], Optional[str]]:
        """Fetch main file from space"""
        file_patterns = self._get_file_patterns_for_sdk(sdk)
        
        for file_pattern in file_patterns:
            try:
                content_path = self.api.hf_hub_download(
                    repo_id=f"{username}/{project_name}",
                    filename=file_pattern,
                    repo_type="space"
                )
                with open(content_path, 'r', encoding='utf-8') as f:
                    return file_pattern, f.read()
            except:
                continue
        
        return None, None
    
    def _get_file_patterns_for_sdk(self, sdk: str) -> List[str]:
        """Get file patterns to try based on SDK"""
        patterns = {
            "static": ["index.html"],
            "gradio": ["app.py", "main.py", "gradio_app.py"],
            "streamlit": [
                "streamlit_app.py", "src/streamlit_app.py",
                "app.py", "src/app.py",
                "main.py", "src/main.py",
                "Home.py", "src/Home.py"
            ]
        }
        
        return patterns.get(sdk, ["app.py", "main.py", "index.html"])
    
    def _detect_language_from_sdk(self, sdk: str, files: Optional[Dict[str, str]] = None) -> str:
        """Detect language/framework from SDK and optionally file contents"""
        # For static SDK, check if it's a transformers.js space by examining files
        if sdk == "static" and files:
            # Check if any JS file contains transformers.js imports
            for filename, content in files.items():
                if filename.endswith(('.js', '.mjs')) or filename == 'index.html':
                    if content and ('@xenova/transformers' in content or '@huggingface/transformers' in content):
                        return "transformers.js"
        
        sdk_map = {
            "gradio": "gradio",
            "streamlit": "streamlit",
            "static": "html",
            "docker": "docker"
        }
        return sdk_map.get(sdk, "python")
    
    def _generate_inference_code(self, model_id: str, pipeline_tag: Optional[str]) -> Optional[str]:
        """Generate inference provider code based on pipeline tag"""
        if not pipeline_tag:
            return None
        
        templates = {
            "text-generation": f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(api_key=os.environ["HF_TOKEN"])

completion = client.chat.completions.create(
    model="{model_id}",
    messages=[
        {{"role": "user", "content": "What is the capital of France?"}}
    ],
)

print(completion.choices[0].message)''',
            
            "text-to-image": f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(api_key=os.environ["HF_TOKEN"])

# output is a PIL.Image object
image = client.text_to_image(
    "Astronaut riding a horse",
    model="{model_id}",
)

# Save the image
image.save("output.png")''',
            
            "automatic-speech-recognition": f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(api_key=os.environ["HF_TOKEN"])

with open("audio.mp3", "rb") as f:
    audio_data = f.read()

result = client.automatic_speech_recognition(
    audio_data,
    model="{model_id}",
)

print(result)''',
            
            "text-to-speech": f'''import os
from huggingface_hub import InferenceClient

client = InferenceClient(api_key=os.environ["HF_TOKEN"])

audio = client.text_to_speech(
    "Hello world",
    model="{model_id}",
)

# Save the audio
with open("output.mp3", "wb") as f:
    f.write(audio)''',
        }
        
        return templates.get(pipeline_tag)
    
    def _fetch_hf_model_readme(self, repo_id: str) -> Optional[str]:
        """Fetch README from HuggingFace model"""
        try:
            local_path = self.api.hf_hub_download(
                repo_id=repo_id,
                filename="README.md",
                repo_type="model"
            )
            with open(local_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return None
    
    def _fetch_github_readme(self, owner: str, repo: str) -> Optional[str]:
        """Fetch README from GitHub repository"""
        urls = [
            f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md",
        ]
        
        for url in urls:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200 and resp.text:
                    return resp.text
            except:
                continue
        
        return None
    
    def _extract_code_from_markdown(self, markdown: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract relevant code from markdown"""
        if not markdown:
            return None, None
        
        # Find all code blocks
        code_blocks = []
        for match in re.finditer(r"```([\w+-]+)?\s*\n([\s\S]*?)```", markdown, re.IGNORECASE):
            lang = (match.group(1) or "").lower()
            code = match.group(2) or ""
            code_blocks.append((lang, code.strip()))
        
        # Score blocks based on relevance
        def score_block(code: str) -> int:
            score = 0
            keywords = [
                "from transformers", "import transformers", "pipeline(",
                "AutoModel", "AutoTokenizer", "text-generation",
                "from diffusers", "import diffusers", "DiffusionPipeline",
                "StableDiffusion", "from gradio", "import gradio"
            ]
            for kw in keywords:
                if kw in code:
                    score += 1
            score += min(len(code) // 200, 5)
            return score
        
        # Filter and sort
        relevant = [
            cb for cb in code_blocks
            if any(kw in cb[1] for kw in ["transformers", "diffusers", "pipeline(", "gradio", "import"])
        ]
        
        if relevant:
            sorted_blocks = sorted(relevant, key=lambda x: score_block(x[1]), reverse=True)
            return sorted_blocks[0][0] or "python", sorted_blocks[0][1]
        
        return None, None
    
    def _extract_transformersjs_code(self, readme: str, model_id: str) -> Optional[str]:
        """Extract Transformers.js code from README"""
        if not readme:
            return None
        
        # Find all code blocks
        code_blocks = []
        for match in re.finditer(r"```([\w+-]+)?\s*\n([\s\S]*?)```", readme, re.IGNORECASE):
            lang = (match.group(1) or "").lower()
            code = match.group(2) or ""
            code_blocks.append((lang, code.strip()))
        
        # Look for JavaScript/TypeScript blocks with Transformers.js code
        for lang, code in code_blocks:
            if lang in ('js', 'javascript', 'ts', 'typescript'):
                # Check if it contains Transformers.js imports
                if '@huggingface/transformers' in code or '@xenova/transformers' in code:
                    return code
        
        # If no specific block found, generate default Transformers.js code
        return self._generate_transformersjs_code(model_id)
    
    def _generate_transformersjs_code(self, model_id: str) -> str:
        """Generate default Transformers.js code for a model"""
        return f'''import {{ pipeline, TextStreamer }} from "@huggingface/transformers";

// Create a text generation pipeline
const generator = await pipeline(
  "text-generation",
  "{model_id}",
  {{ dtype: "fp32" }},
);

// Define the list of messages
const messages = [
  {{ role: "system", content: "You are a helpful assistant." }},
  {{ role: "user", content: "Write a poem about machine learning." }},
];

// Generate a response
const output = await generator(messages, {{
  max_new_tokens: 512,
  do_sample: false,
  streamer: new TextStreamer(generator.tokenizer, {{
    skip_prompt: true,
    skip_special_tokens: true,
    // callback_function: (text) => {{ /* Optional callback function */ }},
  }}),
}});
console.log(output[0].generated_text.at(-1).content);'''


# ==================== CLI Interface ====================

def main():
    """CLI interface for project importer"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Import projects from HuggingFace Spaces, Models, or GitHub repos"
    )
    parser.add_argument("url", help="URL to import from")
    parser.add_argument("-o", "--output", help="Output file to save code", default=None)
    parser.add_argument("--prefer-local", action="store_true", 
                       help="Prefer local inference code over serverless (for models)")
    parser.add_argument("--token", help="HuggingFace token", default=None)
    
    args = parser.parse_args()
    
    # Initialize importer
    importer = ProjectImporter(hf_token=args.token)
    
    # Import project
    print(f"Importing from: {args.url}")
    print("-" * 60)
    
    result = importer.import_from_url(args.url)
    
    # Print results
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Language: {result['language']}")
    print(f"URL: {result['url']}")
    
    if result.get('metadata'):
        print(f"Metadata: {result['metadata']}")
    
    print("-" * 60)
    
    if result['code']:
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result['code'])
            print(f"Code saved to: {args.output}")
        else:
            print("Code:")
            print("=" * 60)
            print(result['code'])
            print("=" * 60)
    else:
        print("No code to display")


if __name__ == "__main__":
    main()

