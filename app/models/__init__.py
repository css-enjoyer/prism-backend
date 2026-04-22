from sqlalchemy.orm import DeclarativeBase

from .analysis import Analysis as Analysis


# Define the shared base class for all models
class Base(DeclarativeBase):
    pass
