"""server.py — AI Functional Consultant v2.0. Run: uvicorn server:app --reload --port 8000"""
import os,sys
sys.path.insert(0,os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import router

app=FastAPI(title="AI Functional Consultant",version="2.0.0",
            description="MP4 interviews -> MoM -> Knowledge Base -> BRD/FRD/Gap/Process/Best Practices (Word + diagrams)")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router,prefix="/api")

@app.get("/health")
def health(): return {"status":"ok","version":"2.0.0"}

_build=os.path.join(os.path.dirname(__file__),"..","frontend","public")
if os.path.exists(_build):
    app.mount("/",StaticFiles(directory=_build,html=True),name="static")

if __name__=="__main__":
    import uvicorn
    uvicorn.run("server:app",host=os.getenv("HOST","0.0.0.0"),port=int(os.getenv("PORT",8000)),reload=True)
