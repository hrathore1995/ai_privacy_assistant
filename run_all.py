# runs backend + serves frontend
import os
import uvicorn
from fastapi.staticfiles import StaticFiles

# import your existing FastAPI app (endpoints, CORS, etc.)
from main import app as backend_app

# mount the frontend at /ui (so no route conflicts with your API)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
os.makedirs(FRONTEND_DIR, exist_ok=True)  # safe if already exists
backend_app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")

if __name__ == "__main__":
    # one port for everything
    PORT = int(os.getenv("PORT", "8000"))
    print(f"\nUI:  http://127.0.0.1:{PORT}/ui/")
    print(f"API: http://127.0.0.1:{PORT}/docs\n")
    uvicorn.run(backend_app, host="0.0.0.0", port=PORT)
