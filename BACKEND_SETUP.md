# Backend Setup & Running Instructions

## Prerequisites

1. **Python 3.11+** installed
2. **Environment variables** configured in `.env` file:
   - `GROQ_API_KEY` - Your Groq API key
   - `MONGO_URI` - Your MongoDB connection string
   - `VOYAGE_API_KEY` - Your Voyage AI API key (for embeddings)
   - `SMTP_EMAIL` - Email for sending notifications (optional)
   - `SMTP_PASSWORD` - Email password (optional)
   - `SMTP_SERVER` - SMTP server (defaults to smtp.gmail.com)
   - `SMTP_PORT` - SMTP port (defaults to 465)

## Installation

1. **Install dependencies** (if using uv):
   ```bash
   uv sync
   ```

   Or if using pip:
   ```bash
   pip install -e .
   ```

## Running the Backend

**IMPORTANT**: Always run from the **project root directory** (where `pyproject.toml` is located), not from inside `src/backend/`.

### Option 1: Using Python module (Recommended)
From the project root:
```bash
python -m src.backend.main
```

### Option 2: Using uvicorn directly (Recommended)
From the project root:
```bash
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Using uvicorn with specific settings
From the project root:
```bash
uvicorn src.backend.main:app --reload --port 8000
```

### Quick Start Command
```bash
# Make sure you're in the project root, then:
cd "/Users/ayush/Desktop/Orbit meet - Update code 1/OrbitMeetAI"
uvicorn src.backend.main:app --reload --port 8000
```

## Verify Backend is Running

Once started, you should see:
- Server running on `http://0.0.0.0:8000` or `http://localhost:8000`
- API documentation available at `http://localhost:8000/docs`
- Health check at `http://localhost:8000/health`

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - Swagger API documentation
- `GET /transcripts` - List all projects and meetings
- `GET /projects` - List all unique projects
- `GET /project/{project_key}` - Get project data
- `GET /project-by-id/{project_id}` - Get project data by ObjectId
- `POST /orbit-chat` - Chat with OrbitMeetAI
- `POST /process-meeting` - Process a meeting transcript
- `POST /trigger-scheduler` - Manually trigger scheduler

## Troubleshooting

### Port Already in Use
If port 8000 is already in use:
```bash
uvicorn src.backend.main:app --reload --port 8001
```
Then update frontend `.env` to use port 8001.

### Module Not Found Errors
Make sure you're running from the project root directory and dependencies are installed.

### MongoDB Connection Issues
- Verify your `MONGO_URI` in `.env` is correct
- Check if MongoDB is accessible from your network
- Ensure TLS/SSL settings are correct

### API Key Issues
- Verify all required API keys are set in `.env`
- Check that API keys are valid and have proper permissions

## Development Mode

For development with auto-reload:
```bash
uvicorn src.backend.main:app --reload --port 8000
```

The `--reload` flag enables automatic reloading when code changes.

