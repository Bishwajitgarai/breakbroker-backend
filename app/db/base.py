# app/db/base.py
from sqlalchemy.orm import declarative_base

Base = declarative_base()

def import_models():
    # Import all your models here so they register with Base.metadata
    # This import is done once, explicitly called when needed
    from app.models.user import User 
    # add all models here

