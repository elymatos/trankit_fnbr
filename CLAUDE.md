# Trankit 2025 - Project Overview

This is a Trankit-based multilingual NLP toolkit project with a FastAPI web service wrapper.

## Project Structure

- **Root Directory**: `/home/ematos/devel/python/trankit_2025/`
- **Main API Service**: `main.py` - FastAPI application providing NLP endpoints
- **Trankit Library**: `trankit/` - Contains the complete Trankit v1.1.2 NLP toolkit
- **Cache Directory**: `cache/` - Model cache storage for XLM-Roberta models
- **Configuration**: Docker setup with `Dockerfile` and `docker-compose.yml`

## Core Components

### 1. FastAPI Web Service (`main.py`)
- **Technology**: FastAPI with CORS middleware
- **Main Endpoints**:
  - `/tkparser/` - Process batches of text articles for full NLP pipeline
  - `/tkbytoken/` - Process pre-tokenized text for POS tagging and dependency parsing
- **Default Models**: Portuguese (primary), English (secondary) with XLM-Roberta-Large
- **GPU Support**: Configurable (currently disabled in main.py:58)

### 2. Trankit NLP Toolkit (`trankit/`)
- **Version**: 1.1.2 
- **Description**: Light-weight transformer-based toolkit for multilingual NLP
- **Architecture**: Built on XLM-Roberta with adapter-based multilingual support
- **Supported Languages**: 56+ languages with pretrained models
- **Core Tasks**:
  - Sentence segmentation
  - Tokenization 
  - Multi-word token expansion
  - Part-of-speech tagging
  - Morphological feature tagging
  - Dependency parsing
  - Named entity recognition

### 3. Key Modules

#### Pipeline (`trankit/trankit/pipeline.py`)
- **Class**: `Pipeline` - Main interface for NLP processing
- **Features**:
  - Auto language detection mode
  - Multi-language support with `add()` method
  - GPU/CPU processing options
  - Caching system for models
- **Key Methods**:
  - `tokenize()` - Tokenization
  - `posdep()` - POS tagging and dependency parsing  
  - `ner()` - Named entity recognition
  - `lemmatize()` - Lemmatization
  - `__call__()` - Full pipeline processing

#### Configuration (`trankit/trankit/config.py`)
- **Class**: `Config` - Central configuration management
- **Key Settings**:
  - Embedding: XLM-Roberta (base/large)
  - Learning rates, dropout, weight decay parameters
  - Model architecture settings

## Dependencies

### Main Project (`requirements.txt`)
- `numpy<2`
- `fastapi[standard]>=0.113.0,<0.114.0`
- `pydantic>=2.7.0,<3.0.0`
- `trankit==1.1.0`

### Trankit Dependencies (`trankit/setup.py`)
- `transformers==4.36.2`
- `torch==2.1.2`
- `adapters>=0.1.1`
- Various NLP utilities (sentencepiece, sacremoses, langid, etc.)

## Usage Examples

### FastAPI Service
```python
# Start service
# uvicorn main:app --host 0.0.0.0 --port 8000

# Process full text
POST /tkparser/
{
  "articles": [{"text": "Hello world!"}],
  "tokens": [],
  "model": "portuguese"
}

# Process tokens
POST /tkbytoken/  
{
  "articles": [],
  "tokens": ["Hello", "world", "!"],
  "model": "portuguese"  
}
```

### Direct Pipeline Usage
```python
from trankit import Pipeline

# Initialize pipeline
p = Pipeline(lang='portuguese', cache_dir='./cache', gpu=False, embedding='xlm-roberta-large')

# Add additional languages
p.add('english')

# Process text
result = p("This is a sample text.")
tokens_only = p.posdep(["This", "is", "a", "sample"], is_sent=True)
```

## Model Storage

- **Cache Location**: `cache/trankit/xlm-roberta-large/`
- **Model Files**: Tokenizer, tagger, lemmatizer, and NER models per language
- **Download**: Models downloaded automatically on first use
- **Source**: Models from University of Oregon NLP group

## Development Notes

- **GPU Support**: Currently disabled in main service (line 58)
- **Language Detection**: Auto-detection available in Trankit pipeline
- **Multi-language**: Easy to add new languages via `Pipeline.add()`
- **Docker Ready**: Container configuration available
- **Testing**: Extensive test suite in `trankit/trankit/tests/`

## Performance

Trankit outperforms other multilingual toolkits like Stanza in many tasks while maintaining efficiency:
- **English**: +9.36% sentence segmentation, +5.07% UAS, +5.81% LAS vs Stanza
- **Arabic**: +16.36% sentence segmentation improvement
- **Chinese**: +14.50% UAS, +15.00% LAS improvements

## Known Issues & Solutions

### 1. Model Download Error (Fixed)

**Issue**: Portuguese models not downloading due to URL mismatch.
**Error**: `MaxRetryError: HTTPConnectionPool(host='nlp.uoregon.edu', port=80): Max retries exceeded`

**Solution Applied**: 
- Updated `requirements.txt` to use local trankit package (`-e ./trankit`) instead of PyPI version
- Local version (1.1.2) has updated HuggingFace URLs: `https://huggingface.co/uonlp/trankit/resolve/main/models/v1.0.0/`

### 2. Dependency Compatibility Error (Fixed)

**Issue**: Import error with newer `huggingface_hub` versions.
**Error**: `cannot import name 'url_to_filename' from 'huggingface_hub.file_download'`

**Solution Applied**:
- Pinned `adapters==0.3.0` in `trankit/setup.py` 
- Added `huggingface_hub<0.20.0` version constraint
- Ensures compatibility between adapters and huggingface_hub libraries

## Common Commands

```bash
# Install dependencies (rebuild container after fixes)
docker-compose build
docker-compose up

# Run API service locally
python main.py

# Test Trankit directly
cd trankit && python -m trankit.tests.test_all

# Manual installation
pip install -r requirements.txt
```

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │────│   Trankit        │────│  XLM-Roberta    │
│   Web Service   │    │   Pipeline       │    │  + Adapters     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                        │
         │                       │                        │
    ┌────▼────┐             ┌────▼────┐              ┌────▼────┐
    │ CORS    │             │Language │              │Model    │
    │Handling │             │Detection│              │Cache    │
    └─────────┘             └─────────┘              └─────────┘
```

This setup provides a robust, scalable multilingual NLP service with state-of-the-art transformer models.