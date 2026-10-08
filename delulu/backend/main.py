import os
import sys

# Ensure root directory is on python sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse, Response

from delulu.database.db import engine, Base
from delulu.backend.routers import (
    auth,
    chat,
    memory,
    files,
    projects,
    tasks,
    devices,
    settings,
    activity,
    skills,
    voice,
    system,
    rhasspy,
)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DELULU - AI Personal Operating Layer",
    description="Multi-user public AI assistant platform with tenant isolation, memory, and desktop control.",
    version="1.0.0"
)

# CORS setup for public web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(files.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(devices.router)
app.include_router(settings.router)
app.include_router(activity.router)
app.include_router(skills.router)
app.include_router(voice.router)
app.include_router(system.router)
app.include_router(rhasspy.router)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "DELULU AI Platform", "version": "1.0.0"}

# Static Frontend mounting
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(
            os.path.join(frontend_dir, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )

    @app.get("/manifest.json")
    def serve_manifest():
        return FileResponse(
            os.path.join(frontend_dir, "manifest.json"),
            media_type="application/manifest+json",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )

    @app.get("/sw.js")
    def serve_service_worker():
        return FileResponse(
            os.path.join(frontend_dir, "sw.js"),
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
        )

    @app.get("/robots.txt", response_class=PlainTextResponse)
    def serve_robots():
        return "User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: http://localhost:8000/sitemap.xml\n"

    @app.get("/sitemap.xml")
    def serve_sitemap():
        content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>http://localhost:8000/</loc>
    <lastmod>2026-10-07</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
        return Response(content=content, media_type="application/xml")

def run():
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"\n=======================================================")
    print(f"       DELULU PLATFORM SERVER RUNNING")
    print(f"       URL: http://localhost:{port}")
    print(f"=======================================================\n")
    uvicorn.run("delulu.backend.main:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    run()
