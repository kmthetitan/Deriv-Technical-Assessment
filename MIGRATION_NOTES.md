# Migration to OpenRouter Gemma-3-27B-IT

## Summary

Successfully migrated the PostgreSQL Query Optimization Pipeline from Google Gemini-2.0-flash to OpenRouter's google/gemma-3-27b-it:free model.

## Changes Made

### 1. Configuration (.env)
```diff
- GEMINI_API_KEY=
+ OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 2. Dependencies (requirements.txt)
```diff
- google-generativeai==0.3.1
+ requests==2.31.0
```

### 3. LLM Client (llm_client.py)
Complete rewrite of API integration from Google SDK to OpenRouter REST API.

**Before**:
- Imported `google.generativeai` library
- Used `genai.configure(api_key=...)`
- Called `model.generate_content(prompt)`

**After**:
- Imports `requests` library
- Stores API key and endpoint URL
- Makes HTTP POST requests to OpenRouter API
- Parses JSON response with `response.json()["choices"][0]["message"]["content"]`

**API Specification**:
- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Method: POST
- Headers: `Authorization: Bearer {api_key}`, `Content-Type: application/json`
- Payload:
  ```json
  {
    "model": "google/gemma-3-27b-it:free",
    "messages": [{"role": "user", "content": "..."}],
    "max_tokens": 4000,
    "temperature": 0.7
  }
  ```
- Response: Standard OpenAI-compatible chat completion response

### 4. Audit Log
LLM calls logged to `llm_calls.jsonl` now show:
```json
{
  "stage": "SCHEMA_ANALYSED",
  "provider": "openrouter",
  "model": "google/gemma-3-27b-it:free",
  ...
}
```

### 5. Documentation
Updated all documentation files:
- **README.md**: Changed API references from Google Gemini to OpenRouter
- **SETUP_GUIDE.md**: Updated setup instructions and troubleshooting
- **IMPLEMENTATION_SUMMARY.md**: Added LLM model specification section

## Unchanged Components

The following components required **no changes** and work as-is:
- `parser.py` - SQL parsing (model-agnostic)
- `stages.py` - Pipeline stages (generic LLM interface)
- `deduplicator.py` - Deterministic deduplication (no LLM)
- `main.py` - Orchestrator (uses generic `llm.call_llm()`)
- `validate.py` - Validation script (artifact-focused)

## API Comparison

| Aspect | Google Gemini | OpenRouter |
|--------|---------------|-----------|
| **Provider** | Google AI Studio | OpenRouter |
| **Model** | gemini-2.0-flash | google/gemma-3-27b-it:free |
| **API Type** | SDK (google-generativeai) | REST (requests) |
| **Cost** | Free tier | Free tier |
| **Setup** | API key only | API key + endpoint |
| **Response Time** | Fast | Variable (router overhead) |

## Testing

All Python files validated for syntax:
```bash
✓ llm_client.py
✓ parser.py
✓ stages.py
✓ deduplicator.py
✓ main.py
✓ validate.py
```

## Setup Instructions

1. **Get OpenRouter API Key**:
   - Visit https://openrouter.ai/
   - Sign up for free account
   - Generate API key from dashboard

2. **Configure Environment**:
   ```bash
   # Edit .env
   OPENROUTER_API_KEY=sk-or-...
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Pipeline**:
   ```bash
   python main.py
   ```

## Rollback (if needed)

To revert to Google Gemini:

1. Restore `.env`:
   ```
   GEMINI_API_KEY=your_key_here
   ```

2. Restore `requirements.txt`:
   ```
   google-generativeai==0.3.1
   ```

3. Restore `llm_client.py` from git history:
   ```bash
   git checkout HEAD -- llm_client.py
   ```

## Performance Notes

- OpenRouter adds slight latency due to routing layer
- Gemma-3-27B-IT is comparable in quality to GPT-3.5-class models
- Free tier may have rate limits - monitor usage
- Consider caching responses for repeated queries

## Future Enhancements

To use different OpenRouter models, edit `llm_client.py`:

```python
# Line 17
self.model = "google/gemma-3-27b-it:free"  # Change this
```

Available models: https://openrouter.ai/models

Popular alternatives:
- `meta-llama/llama-3-8b-instruct:free`
- `mistralai/mistral-7b-instruct:free`
- `gpt-3.5-turbo` (paid)
- `gpt-4` (paid)

## Support

For OpenRouter issues:
- Documentation: https://openrouter.ai/docs
- Status: https://status.openrouter.ai/

For pipeline issues:
- Check `llm_calls.jsonl` for API response details
- Verify API key is valid and has balance
- Check network connectivity to https://openrouter.ai/api/v1/chat/completions

---

**Migration Date**: April 30, 2026
**Status**: ✅ Complete
**Next Step**: Add OpenRouter API key to .env and run pipeline
