# Hifdh Review App

A Quran memorization review application with real-time transcription feedback. The app listens to your recitation, tracks your progress word-by-word, and identifies mistakes in real-time.

## Features

- **Real-time transcription** using Whisper (Arabic Quran-tuned model)
- **Word-by-word highlighting** as you recite
- **Uthmani script support** - handles differences between Uthmani and standard Arabic
- **Pause/restart handling** - supports natural tajweed practice patterns
- **Mistake detection** - identifies wrong words, skipped words, and more
- **Session summaries** - accuracy stats after each review session

## Architecture

```
├── backend/          # FastAPI + Python
│   ├── alignment/    # Text alignment engine
│   ├── ml/           # Whisper transcription
│   ├── api/          # REST + WebSocket endpoints
│   └── services/     # Business logic
├── frontend/         # React + TypeScript
│   ├── components/   # UI components
│   ├── hooks/        # Audio recording, WebSocket
│   └── services/     # API client
└── scripts/          # Utility scripts
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- ~200MB disk space for the ML model

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/majidtahir1/hifdh.git
cd hifdh
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Download the Whisper Model

The app uses the [tarteel-ai/whisper-base-ar-quran](https://huggingface.co/tarteel-ai/whisper-base-ar-quran) model, converted to CTranslate2 format for faster inference.

**Option A: Download pre-converted model (Recommended)**

```bash
# Create models directory
mkdir -p backend/models/tarteel-quran-ct2

# Download from Hugging Face (if available) or convert yourself
# The model files needed are:
#   - model.bin (~138MB)
#   - config.json
#   - vocabulary.json
```

**Option B: Convert the model yourself**

```bash
pip install transformers ctranslate2

# Convert the Hugging Face model to CTranslate2 format
ct2-transformers-converter \
    --model tarteel-ai/whisper-base-ar-quran \
    --output_dir backend/models/tarteel-quran-ct2 \
    --quantization float16
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

## Running the App

### Start the Backend

```bash
cd backend
source venv/bin/activate
python main.py
```

The API will be available at `http://localhost:8000`

### Start the Frontend

```bash
cd frontend
npm run dev
```

The app will be available at `http://localhost:3000`

### Access from Other Devices (e.g., phone)

```bash
# Frontend with network access
npm run dev -- --host

# Note: Microphone access requires HTTPS on non-localhost
# Use ngrok for testing on mobile:
ngrok http 3000
```

## Usage

1. Select a Juz range to review
2. Listen to the prompt ayah (the ayah before your test portion)
3. Click "Start Recording" and recite the continuation from memory
4. Watch your words highlight in real-time:
   - **Bold black** = correctly recited
   - **Green pulse** = being processed
   - **Red underline** = mistake detected
   - **Gray** = not yet recited
5. Click "Stop" when finished to see your session summary

## Configuration

Key settings in `backend/services/transcription_handler.py`:

```python
MIN_TRANSCRIPTION_DURATION = 0.15  # Minimum audio before processing
TRANSCRIPTION_INTERVAL = 0.15      # How often to run transcription
```

Key settings in `backend/alignment/engine.py`:

```python
STABILITY_THRESHOLD = 1   # Matches needed before confirming (1 = immediate)
DEFAULT_LOOK_BEHIND = 10  # Words to search for restart detection
```

## Running Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test files
pytest tests/test_normalizer.py tests/test_alignment_uthmani.py -v
```

See [TESTING.md](TESTING.md) for the full testing strategy.

## API Endpoints

### REST

- `POST /api/session/start` - Start a new review session
- `GET /api/session/{id}` - Get session details
- `GET /api/quran/ayah/{surah}/{ayah}` - Get specific ayah

### WebSocket

- `ws://localhost:8000/ws/{session_id}` - Real-time audio streaming

Messages:
- `start_recording` - Begin transcription
- `stop_recording` - End and get summary
- Binary frames - Audio chunks (WebM/Opus)

## Troubleshooting

### "Model not found" error

Ensure the model files are in `backend/models/tarteel-quran-ct2/`:
- `model.bin`
- `config.json`
- `vocabulary.json`

### Microphone not working on mobile

Browsers require HTTPS for microphone access on non-localhost. Use ngrok:
```bash
ngrok http 3000
```

### Transcription is slow

- Ensure you're using the CTranslate2 model (not raw Hugging Face)
- Check if GPU is available: the app auto-detects CUDA
- Reduce `TRANSCRIPTION_INTERVAL` for less frequent updates

### Words not matching correctly

The app handles Uthmani script differences, but some edge cases may exist. Check the logs for `[COMPARE]` entries to see what's being compared.

## License

MIT

## Acknowledgments

- [Tarteel AI](https://tarteel.ai/) for the Quran-tuned Whisper model
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) for CTranslate2 Whisper implementation
