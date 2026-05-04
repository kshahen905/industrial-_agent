"""
Configuration for DevOps Log Analyzer

Easily switch between different models and settings here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ==================== MODEL CONFIGURATION ====================

# Available models: phi3:mini, neural-chat, mistral, dolphin-mistral, llama2:13b, orca-mini, tinyllama
# Change this to switch models
DEFAULT_MODEL = os.getenv("LLM_MODEL", "orca-mini")

# Ollama API settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TIMEOUT = 30

# Model parameters
MODEL_TEMPERATURE = 0.3  # Lower = more consistent, Higher = more creative
MODEL_NUM_PREDICT = 128  # Max tokens in response (reduced for low-memory systems)

# Model descriptions for reference
AVAILABLE_MODELS = {
    "phi3:mini": {
        "size": "3.8B parameters",
        "speed": "⚡ Very Fast",
        "quality": "⚠️  Low (Poor for detailed analysis)",
        "memory": "~2GB",
        "recommendation": "❌ NOT recommended for log analysis"
    },
    "neural-chat": {
        "size": "7B parameters",
        "speed": "⚡⚡ Fast",
        "quality": "✓ Good (Balanced quality)",
        "memory": "~5GB",
        "recommendation": "✅ RECOMMENDED - Good balance"
    },
    "mistral": {
        "size": "7B parameters",
        "speed": "⚡⚡ Fast",
        "quality": "✓ Good (Strong reasoning)",
        "memory": "~5GB",
        "recommendation": "✅ RECOMMENDED - Excellent reasoning"
    },
    "dolphin-mistral": {
        "size": "7B parameters",
        "speed": "⚡⚡ Fast",
        "quality": "✓ Very Good (Instructions)",
        "memory": "~5GB",
        "recommendation": "✅ RECOMMENDED - Great for instructions"
    },
    "llama2:13b": {
        "size": "13B parameters",
        "speed": "⚡⚡⚡ Medium",
        "quality": "✓✓ Excellent (Best quality)",
        "memory": "~10GB",
        "recommendation": "✅ BEST - Superior analysis"
    },
    "orca-mini": {
        "size": "3B parameters",
        "speed": "⚡ Very Fast",
        "quality": "✓ Good (Excellent for 3B size)",
        "memory": "~2GB",
        "recommendation": "✅ RECOMMENDED - Best for low-memory systems"
    }
}

# ==================== VECTOR DATABASE ====================

VECTOR_DB_PATH = "./vector_db"
VECTOR_DB_COLLECTION_NAME = "devops_docs"

# ChromaDB settings
CHROMA_HOST = os.getenv("CHROMA_HOST", None)
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

# Embeddings model
EMBEDDINGS_MODEL = "all-MiniLM-L6-v2"
EMBEDDINGS_DEVICE = "cpu"  # Change to "cuda" if you have GPU

# ==================== VECTOR SEARCH ====================

VECTOR_SEARCH_TOP_K = 2  # Number of docs to retrieve (reduced from 6 for memory efficiency)

# ==================== LOGGING ====================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ==================== DATA INGESTION ====================

DOCS_PATH = "./data/docs"

# ==================== HELPER FUNCTIONS ====================

def get_model_info() -> str:
    """Get information about the current model"""
    model_info = AVAILABLE_MODELS.get(DEFAULT_MODEL, {})
    return f"""
╔════════════════════════════════════════════════════════════════╗
║                    CURRENT MODEL SETTINGS                      ║
╚════════════════════════════════════════════════════════════════╝
Model: {DEFAULT_MODEL}
Size: {model_info.get('size', 'Unknown')}
Speed: {model_info.get('speed', 'Unknown')}
Quality: {model_info.get('quality', 'Unknown')}
Memory: {model_info.get('memory', 'Unknown')}
{model_info.get('recommendation', '')}

To change model: Edit DEFAULT_MODEL in config.py or set LLM_MODEL env var
════════════════════════════════════════════════════════════════
"""

def print_available_models():
    """Print all available models and their specs"""
    print("\n" + "="*70)
    print("AVAILABLE MODELS FOR OLLAMA")
    print("="*70)
    for model, info in AVAILABLE_MODELS.items():
        print(f"\n{model}:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    print("\n" + "="*70)
    print("Recommendation: Start with 'neural-chat' or 'mistral'")
    print("="*70)
