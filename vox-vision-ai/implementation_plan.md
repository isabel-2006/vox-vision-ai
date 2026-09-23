# Implementation Plan - Step 1: VoxVision AI Foundation

Build Step 1 of VoxVision AI: a clean, functional frontend and FastAPI backend foundation for a multimodal AI assistant.

## User Review Required

> [!IMPORTANT]
> **Design Philosophy**: The UI will adopt a restrained dark developer-aesthetic layout using neutral charcoal `#121316` / `#1a1c23`, subtle borders, crisp typography, and functional SVG controls. No neon glows or generic AI template looks.
> **Static Serving**: FastAPI will serve the `frontend/` directory statically on port `8000` while also supporting CORS, allowing access either via direct static file serving or via independent live-server testing.

## Proposed Changes

### Project Structure & Configuration

#### [NEW] [.gitignore](file:///c:/Users/LEGION/GIT/vox-vision-ai/.gitignore)
Standard Git ignore file for Python (`__pycache__`, `.venv`, `.env`), IDE configs, OS files.

#### [NEW] [backend/.env.example](file:///c:/Users/LEGION/GIT/vox-vision-ai/backend/.env.example)
Example environment variable template (HOST, PORT, ENV, future API keys placeholders).

#### [NEW] [backend/requirements.txt](file:///c:/Users/LEGION/GIT/vox-vision-ai/backend/requirements.txt)
Minimal dependencies: `fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv`.

---

### Backend (Python + FastAPI)

#### [NEW] [backend/app/main.py](file:///c:/Users/LEGION/GIT/vox-vision-ai/backend/app/main.py)
FastAPI application setup, CORS middleware configuration, route registration (`/api/health`, `/api/chat`), and static file mounting for `frontend/`.

#### [NEW] [backend/app/config.py](file:///c:/Users/LEGION/GIT/vox-vision-ai/backend/app/config.py)
App configuration loader using `pydantic-settings` or `os.getenv`.

#### [NEW] [backend/app/api/health.py](file:///c:/Users/LEGION/GIT/vox-vision-ai/backend/app/api/health.py)
Health check endpoint (`GET /api/health`) returning system status, timestamp, and version.

#### [NEW] [backend/app/api/chat.py](file:///c:/Users/LEGION/GIT/vox-vision-ai/backend/app/api/chat.py)
Placeholder chat test endpoint (`POST /api/chat/placeholder`) to verify backend-frontend connectivity.

---

### Frontend (HTML / Vanilla CSS / Vanilla JS)

#### [NEW] [frontend/index.html](file:///c:/Users/LEGION/GIT/vox-vision-ai/frontend/index.html)
Semantic HTML layout including:
- Header with VoxVision AI logo mark, title, subline, and backend live connection badge.
- Main message scroll area with empty-state introduction box explaining VoxVision AI capabilities (Multimodal Speech, Vision, and Text).
- Message input toolbar with auto-expanding text input, send button, and clearly labeled disabled/placeholder action buttons for Microphone, Image, and Camera ("Voice coming soon", "Vision coming soon").

#### [NEW] [frontend/styles.css](file:///c:/Users/LEGION/GIT/vox-vision-ai/frontend/styles.css)
Restrained dark CSS design system:
- HSL/Hex color variables (`#0d0e11`, `#16181d`, `#222630`, `#363d4e`, soft accent `#3b82f6`).
- Responsive flexbox/grid layout (desktop side-padded view, edge-to-edge mobile view).
- Crisp micro-interactions (subtle hover states, clear disabled/coming-soon tooltips, active status pulse).

#### [NEW] [frontend/app.js](file:///c:/Users/LEGION/GIT/vox-vision-ai/frontend/app.js)
Frontend logic handling:
- Server health check polling & UI badge update.
- Local chat message rendering (user input + assistant mock response).
- Input auto-resize and keyboard shortcuts (Enter to send, Shift+Enter for newline).
- Toast / notification feedback when clicking disabled buttons ("Microphone integration coming in Step 2", etc.).

## Verification Plan

### Automated Tests / Health Check
- Run FastAPI backend locally using `python -m uvicorn app.main:app --port 8000`.
- Verify `/api/health` returns status 200 OK via HTTP request.

### Manual & UI Verification
- Open `http://localhost:8000` in browser.
- Verify VoxVision AI header, connection badge ("Connected"), empty state card, and input bar load seamlessly.
- Send a test message and verify it appears in the conversation area along with a placeholder assistant reply.
- Click disabled control buttons (Microphone, Image, Camera) and verify "Coming soon" toast/tooltip behavior.
- Test responsive view for mobile screen widths (375px) and desktop screen widths (1280px).
