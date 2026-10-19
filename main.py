import uvicorn
from fastapi import FastAPI

from tracker_pro.api import auth, agent, health, meal, task

tracker_app = FastAPI(title="Tracker Pro")
tracker_app.include_router(health.health_router)
tracker_app.include_router(auth.auth_router)
tracker_app.include_router(task.task_router)
tracker_app.include_router(meal.meal_router)
tracker_app.include_router(agent.agent_router)


if __name__ == "__main__":
    uvicorn.run(tracker_app, host="127.0.0.1", port=8000)
