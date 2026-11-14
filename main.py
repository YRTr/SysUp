from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scanner import scan_system_specs
from geo_pricing import get_user_location
from recommender import WORKLOAD_PROFILES, generate_recommendation

app = FastAPI(title="Hardware Spec & Upgrade Advisor API")

# Allow CORS for local React frontend development (Vite/CRA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache specs and location on startup so switching workloads in the UI is instant
CACHED_SPECS = None
CACHED_LOCATION = None

class EvaluateRequest(BaseModel):
    goal_key: str
    force_rescan: bool = False

@app.get("/api/status")
def get_initial_status():
    """Return current hardware specs, detected location, and available workload goals."""
    global CACHED_SPECS, CACHED_LOCATION
    if not CACHED_SPECS:
        CACHED_SPECS = scan_system_specs()
    if not CACHED_LOCATION:
        CACHED_LOCATION = get_user_location()

    available_goals = [
        {"key": k, "title": v["title"], "tier": v["tier"]}
        for k, v in WORKLOAD_PROFILES.items()
    ]

    return {
        "specs": CACHED_SPECS,
        "location": CACHED_LOCATION,
        "available_goals": available_goals
    }

@app.post("/api/evaluate")
def evaluate_workload(req: EvaluateRequest):
    """Evaluate system against selected workload and return localized upgrade paths."""
    global CACHED_SPECS, CACHED_LOCATION

    if req.force_rescan or not CACHED_SPECS:
        CACHED_SPECS = scan_system_specs()
    if req.force_rescan or not CACHED_LOCATION:
        CACHED_LOCATION = get_user_location()

    try:
        report = generate_recommendation(req.goal_key, CACHED_SPECS, CACHED_LOCATION)
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)