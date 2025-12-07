# OrbitMeetAI

An intelligent meeting analysis platform that automatically processes meeting transcripts, generates comprehensive summaries, analyzes participant contributions, and provides an AI-powered chatbot for project insights.

## 📋 Table of Contents

- [Overview](#overview)
- [Objectives](#objectives)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Project](#running-the-project)
- [API Endpoints](#api-endpoints)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

OrbitMeetAI is a full-stack application that leverages AI agents to automatically analyze meeting transcripts. The system processes raw meeting transcripts through a multi-agent orchestration workflow, generating:

- **Meeting Summaries**: Concise bullet-point summaries of key discussion points
- **Participant Analysis**: Individual analysis of each participant's contributions, updates, roadblocks, and action items
- **Project Summaries**: Global project-level insights aggregated across multiple meetings
- **AI Chatbot**: Context-aware chatbot that answers questions about projects using RAG (Retrieval Augmented Generation)

The platform uses LangGraph for agent orchestration, MongoDB for data storage, and provides both REST API and React frontend interfaces.

## 🎯 Objectives

1. **Automate Meeting Analysis**: Eliminate manual note-taking and summary generation
2. **Extract Actionable Insights**: Identify key updates, roadblocks, and action items for each participant
3. **Provide Project-Level Intelligence**: Aggregate insights across multiple meetings to understand project progress
4. **Enable Interactive Querying**: Allow users to ask questions about projects and get AI-powered answers
5. **Streamline Communication**: Automatically send email summaries to participants and executives

## ✨ Features

### Core Capabilities

- **Multi-Agent Orchestration**: Uses specialized AI agents for different analysis tasks
- **Meeting Summary Generation**: Extracts 8-10 key points from meeting transcripts
- **Participant Analysis**: Analyzes individual contributions, updates, roadblocks, and action items
- **Project Aggregation**: Combines insights from multiple meetings into project-level summaries
- **MongoDB Integration**: Stores transcripts, summaries, and analysis results
- **Automated Email Notifications**: Sends summaries to participants and executives
- **Scheduled Processing**: Background scheduler for automatic processing of new meetings
- **RAG-Powered Chatbot**: Answers questions using project context from MongoDB
- **Modern Web Interface**: React-based frontend with responsive design

### Technical Features

- FastAPI backend with async support
- LangGraph workflow orchestration
- Groq LLM integration for fast inference
- Voyage AI embeddings for vector search
- MongoDB Atlas with vector search capabilities
- React + Vite frontend
- Tailwind CSS for styling

## 🏗️ Architecture

The system follows a multi-agent architecture pattern:

```
┌─────────────────┐
│  Meeting        │
│  Transcript     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      Orchestrator Workflow          │
│  (LangGraph State Machine)          │
└────────┬────────────────────────────┘
         │
         ├──► Meeting Summary Agent
         ├──► Participant Analysis Agent
         ├──► Project Summary Agent
         │
         ▼
┌─────────────────────────────────────┐
│         MongoDB Storage              │
│  - Raw Transcripts                   │
│  - Meeting Summaries                 │
│  - Participant Analysis              │
│  - Project Summaries                 │
└────────┬────────────────────────────┘
         │
         ├──► Email Notifications
         └──► Frontend Dashboard
              └──► AI Chatbot (RAG)
```

### Agent Workflow

1. **Meeting Summary Agent**: Generates concise meeting summaries
2. **Participant Analyst Agent**: Analyzes individual participant contributions
3. **Project Summary Agent**: Creates aggregated project-level insights
4. **Orchestrator**: Coordinates the workflow and manages state

## 📁 Project Structure

```
OrbitMeetAI/
├── src/
│   ├── Agentic/                    # AI Agent System
│   │   ├── agents/
│   │   │   ├── MeetingSummaryAgent.py      # Meeting summary generation
│   │   │   ├── ParticipantAnalystAgent.py  # Participant analysis
│   │   │   ├── ProjectSummaryAgent.py      # Project-level summaries
│   │   │   └── Orchestrator.py             # Workflow orchestration
│   │   └── utils/
│   │       ├── pydantic_schemas.py         # Data models
│   │       ├── store_to_mongodb.py         # MongoDB operations
│   │       └── tools.py                    # Utility functions
│   │
│   ├── backend/                     # FastAPI Backend
│   │   ├── main.py                  # API endpoints
│   │   └── scheduler.py             # Background job scheduler
│   │
│   ├── chatbot/                     # AI Chatbot
│   │   └── orbit_chat.py            # RAG-based chat implementation
│   │
│   └── frontend/                    # React Frontend
│       ├── src/
│       │   ├── components/          # React components
│       │   ├── contexts/            # React contexts
│       │   └── services/           # API service layer
│       └── package.json
│
├── SampleData/                      # Sample transcripts and data
├── pyproject.toml                   # Python dependencies
├── run_backend.sh                   # Backend startup script
└── README.md                        # This file
```

## 🔧 Prerequisites

Before installing and running the project, ensure you have:

1. **Python 3.11+** installed
2. **Node.js 18+** and npm installed (for frontend)
3. **MongoDB Atlas** account (or local MongoDB instance)
4. **API Keys**:
   - Groq API key ([get one here](https://console.groq.com/))
   - Voyage AI API key ([get one here](https://www.voyageai.com/))
   - MongoDB connection string

## 📦 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd OrbitMeetAI
```

### 2. Install Python Dependencies

The project uses `uv` for dependency management. Install dependencies:

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 3. Install Frontend Dependencies

```bash
cd src/frontend
npm install
cd ../..
```

## ⚙️ Configuration

Create a `.env` file in the project root directory with the following variables:

```env
# Required API Keys
GROQ_API_KEY=your_groq_api_key_here
MONGO_URI=your_mongodb_connection_string_here
VOYAGE_API_KEY=your_voyage_api_key_here

# Email Configuration (Optional - for email notifications)
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
```

### MongoDB Setup

1. Create a MongoDB Atlas cluster (or use local MongoDB)
2. Create a database named `OMNI_MEET_DB`
3. The following collections will be created automatically:
   - `Raw_Transcripts`: Stores meeting transcripts
   - `Meeting_summary`: Stores meeting summaries
   - `Participant_summary`: Stores participant analysis
   - `Project_summary`: Stores project-level summaries

### Frontend Environment (Optional)

Create a `.env` file in `src/frontend/`:

```env
VITE_API_URL=http://localhost:8000
```

If not set, it defaults to `http://localhost:8000`.

## 🚀 Running the Project

### Backend Setup

**IMPORTANT**: Always run the backend from the **project root directory** (where `pyproject.toml` is located).

#### Option 1: Using the Shell Script (Easiest)

```bash
chmod +x run_backend.sh
./run_backend.sh
```

#### Option 2: Using uvicorn Directly

```bash
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option 3: Using Python Module

```bash
python -m src.backend.main
```

The backend will start on `http://localhost:8000`

### Frontend Setup

Open a new terminal and run:

```bash
cd src/frontend
npm run dev
```

The frontend will start on `http://localhost:5173` (or another port if 5173 is busy)

### Verify Installation

1. **Backend Health Check**: Visit `http://localhost:8000/health`
2. **API Documentation**: Visit `http://localhost:8000/docs` (Swagger UI)
3. **Frontend**: Visit `http://localhost:5173`

## 📡 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint (health check) |
| `GET` | `/health` | Service health status |
| `GET` | `/docs` | Swagger API documentation |
| `POST` | `/process-meeting` | Process a meeting transcript |
| `GET` | `/project/{project_key}` | Get project data by project key |
| `GET` | `/project-by-id/{project_id}` | Get project data by MongoDB ObjectId |
| `GET` | `/transcripts` | List all transcripts |
| `GET` | `/projects` | List all unique projects |
| `POST` | `/orbit-chat` | Chat with OrbitMeetAI about a project |
| `POST` | `/trigger-scheduler` | Manually trigger scheduler |

### Example: Process a Meeting

```bash
curl -X POST "http://localhost:8000/process-meeting" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "Meeting transcript text here...",
    "project_key": "project-001",
    "project_name": "Project Alpha",
    "meeting_name": "Sprint Planning",
    "participants": ["Alice", "Bob", "Charlie"]
  }'
```

### Example: Chat with OrbitMeetAI

```bash
curl -X POST "http://localhost:8000/orbit-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Project Alpha",
    "question": "What were the main roadblocks discussed?"
  }'
```

## 💻 Usage

### Processing a Meeting

1. **Via API**: Use the `/process-meeting` endpoint with a meeting transcript
2. **Via Scheduler**: The background scheduler automatically processes new meetings from MongoDB
3. **Manual Trigger**: Use `/trigger-scheduler` to manually trigger processing

### Using the Frontend

1. **Select a Project**: Choose from the dropdown of available projects
2. **View Summaries**: 
   - Meeting Summary (collapsible)
   - Participant Analysis (collapsible)
   - Project Summary (collapsible)
3. **Chat with AI**: Ask questions about the project in the chatbot panel

### Workflow Process

When a meeting is processed, the system:

1. Generates meeting summary (8-10 key points)
2. Analyzes each participant's contributions
3. Saves data to MongoDB
4. Fetches project history
5. Generates global project summary
6. Sends email notifications (if configured)

## 🔍 Troubleshooting

### Backend Issues

#### Port Already in Use
```bash
# Use a different port
uvicorn src.backend.main:app --reload --port 8001
```

#### Module Not Found Errors
- Ensure you're running from the project root directory
- Verify dependencies are installed: `uv sync` or `pip install -e .`

#### MongoDB Connection Issues
- Verify `MONGO_URI` in `.env` is correct
- Check MongoDB network access settings
- Ensure TLS/SSL settings are correct for MongoDB Atlas

#### API Key Issues
- Verify all required API keys are set in `.env`
- Check that API keys are valid and have proper permissions
- Ensure no extra spaces or quotes in `.env` file

### Frontend Issues

#### Cannot Connect to Backend
- Verify backend is running on port 8000
- Check `VITE_API_URL` in frontend `.env` matches backend port
- Check CORS settings in backend (should allow frontend origin)

#### Build Errors
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Common Errors

#### "Workflow not initialized"
- Wait a few seconds after starting the backend for initialization
- Check logs for initialization errors

#### "Project not found"
- Ensure the project exists in MongoDB
- Verify project name matches exactly (case-sensitive)

#### Email Sending Fails
- Email configuration is optional; the system will continue without it
- For Gmail, use an App Password, not your regular password

## 🛠️ Development

### Running in Development Mode

Backend with auto-reload:
```bash
uvicorn src.backend.main:app --reload --port 8000
```

Frontend with hot-reload:
```bash
cd src/frontend
npm run dev
```

### Testing

Test the orchestrator workflow:
```bash
python orchestrator_test.py
```

### Project Dependencies

Key Python packages:
- `fastapi`: Web framework
- `langchain`: LLM framework
- `langchain-groq`: Groq LLM integration
- `langgraph`: Workflow orchestration
- `pymongo`: MongoDB driver
- `uvicorn`: ASGI server

Key Frontend packages:
- `react`: UI framework
- `vite`: Build tool
- `axios`: HTTP client
- `tailwindcss`: CSS framework

## 📝 Notes

- The scheduler runs hourly to process unprocessed meetings
- All data is stored in MongoDB collections
- The chatbot uses RAG with MongoDB vector search
- Email notifications require SMTP configuration

## 📄 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Support

[Add support/contact information here]

---

**Built with ❤️ using FastAPI, LangGraph, React, and MongoDB**

