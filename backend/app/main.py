from fastapi import FastAPI
from .core.db import init_db
from .api.routes import r
app=FastAPI(title='DalilDZ',version='1.0.0');app.include_router(r)
@app.on_event('startup')
def startup():init_db()
