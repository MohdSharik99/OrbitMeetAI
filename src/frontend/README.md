# OrbitMeetAI Frontend

A modern React frontend for the OrbitMeetAI meeting analysis dashboard.

## Features

- **Project & Meeting Selection**: Dropdown selectors to choose from available projects and meetings
- **Meeting Analysis Dashboard**: 
  - Meeting Summary (collapsible)
  - Participant Analysis (collapsible)
  - Project Summary (collapsible)
- **AI Chatbot**: Context-aware chatbot using the OrbitMeetAI chat endpoint
- **80:20 Layout**: Responsive split layout with summaries on the left (80%) and chatbot on the right (20%)

## Setup

1. Install dependencies:
```bash
cd src/frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

## Environment Variables

Create a `.env` file in the frontend directory (optional):
```
VITE_API_URL=http://localhost:8000
```

If not set, it defaults to `http://localhost:8000`

## Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Backend Requirements

Make sure the backend API is running on port 8000 with the following endpoints:
- `GET /transcripts` - List all projects and meetings
- `GET /project/{project_key}` - Get project data
- `POST /orbit-chat` - Chat with OrbitMeetAI

## Tech Stack

- React 18
- Vite
- Tailwind CSS
- Axios

