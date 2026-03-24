from sqlalchemy.orm import DeclarativeBase

# Define the shared base class for all models
class Base(DeclarativeBase):
    pass

# Import models so they’re exposed at package level
from .analysis import Analysis
