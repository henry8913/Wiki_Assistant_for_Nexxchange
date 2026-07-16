from pathlib import Path

from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from agno.os.app import AgentOS

from wiki_assistant.agent import get_agent
from wiki_assistant.config import APP_ENV, HOST, PORT
from wiki_assistant.db import session_db
from wiki_assistant.knowledge import get_wiki_knowledge

agent = get_agent()
agent.db = session_db
agent.add_history_to_context = True
agent.num_history_runs = 5

knowledge = get_wiki_knowledge()

agent_os = AgentOS(
    agents=[agent],
    knowledge=[knowledge],
)

app = agent_os.get_app()

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/chat")
    async def chat_page():
        return FileResponse(str(static_dir / "chat.html"))

img_dir = Path(__file__).parent.parent / "IMG"
if img_dir.exists():
    app.mount("/img", StaticFiles(directory=str(img_dir)), name="img")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    agent_os.serve(
        app="wiki_assistant.main:app",
        host=HOST,
        port=PORT,
        reload=(APP_ENV == "development"),
    )
