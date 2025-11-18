"""
Example usage of the ProjectImporter module

This script demonstrates how to use the standalone project importer
to fetch code from various sources without Gradio.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_importer import ProjectImporter


def example_import_space():
    """Example: Import a HuggingFace Space"""
    print("=" * 80)
    print("Example 1: Importing a HuggingFace Space")
    print("=" * 80)
    
    importer = ProjectImporter()
    result = importer.import_space("akhaliq", "anycoder")
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Language: {result['language']}")
    print(f"Files: {len(result['metadata'].get('files', []))}")
    print(f"\nFirst 500 characters of code:\n{result['code'][:500]}...")
    print()


def example_import_model():
    """Example: Import a HuggingFace Model"""
    print("=" * 80)
    print("Example 2: Importing a HuggingFace Model")
    print("=" * 80)
    
    importer = ProjectImporter()
    result = importer.import_model("meta-llama/Llama-3.2-1B-Instruct")
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Language: {result['language']}")
    print(f"Pipeline Tag: {result['metadata'].get('pipeline_tag')}")
    print(f"\nCode:\n{result['code']}")
    print()


def example_import_github():
    """Example: Import a GitHub Repository"""
    print("=" * 80)
    print("Example 3: Importing from GitHub")
    print("=" * 80)
    
    importer = ProjectImporter()
    result = importer.import_github_repo("huggingface", "transformers")
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Language: {result['language']}")
    print(f"\nFirst 500 characters of code:\n{result['code'][:500]}...")
    print()


def example_import_from_url():
    """Example: Import from any URL"""
    print("=" * 80)
    print("Example 4: Import from URL (automatic detection)")
    print("=" * 80)
    
    importer = ProjectImporter()
    
    # Test different URL types
    urls = [
        "https://huggingface.co/spaces/akhaliq/anycoder",
        "https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct",
        "https://github.com/huggingface/diffusers"
    ]
    
    for url in urls:
        print(f"\nImporting: {url}")
        result = importer.import_from_url(url)
        print(f"  Status: {result['status']}")
        print(f"  Language: {result['language']}")
        print(f"  Message: {result['message']}")


def example_save_to_file():
    """Example: Save imported code to a file"""
    print("=" * 80)
    print("Example 5: Save imported code to file")
    print("=" * 80)
    
    importer = ProjectImporter()
    result = importer.import_model("stabilityai/stable-diffusion-3.5-large")
    
    if result['status'] == 'success':
        output_file = "imported_sd3.5_code.py"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result['code'])
        print(f"Code saved to: {output_file}")
    else:
        print(f"Failed to import: {result['message']}")
    print()


def example_with_metadata():
    """Example: Working with metadata"""
    print("=" * 80)
    print("Example 6: Working with metadata")
    print("=" * 80)
    
    importer = ProjectImporter()
    result = importer.import_model("Qwen/Qwen2.5-Coder-32B-Instruct")
    
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"\nMetadata:")
    for key, value in result['metadata'].items():
        print(f"  {key}: {value}")
    
    # Check if there are alternatives
    if result['metadata'].get('has_alternatives'):
        print("\n✨ This model has multiple code options available!")
        print("  - Inference code (serverless)")
        print("  - Local code (transformers/diffusers)")
    print()


def main():
    """Run all examples"""
    print("\n🚀 ProjectImporter Examples\n")
    
    try:
        example_import_space()
    except Exception as e:
        print(f"❌ Space import failed: {e}\n")
    
    try:
        example_import_model()
    except Exception as e:
        print(f"❌ Model import failed: {e}\n")
    
    try:
        example_import_github()
    except Exception as e:
        print(f"❌ GitHub import failed: {e}\n")
    
    try:
        example_import_from_url()
    except Exception as e:
        print(f"❌ URL import failed: {e}\n")
    
    try:
        example_with_metadata()
    except Exception as e:
        print(f"❌ Metadata example failed: {e}\n")
    
    print("\n✅ Examples completed!")


if __name__ == "__main__":
    main()

