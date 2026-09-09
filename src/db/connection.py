    # Postgress Connection / SQLAlchemy engine 

import os 

from dotenv import load_dotenv
from sqlalchemy import create_engine 
from sqlalchemy.engine import Engine 

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://analytics_user:analytics_pass@localhost:5432/analytics_db"
)

_engine: Engine | None = None 

def get_engine() -> Engine: 
        """Return a singleton SQLAlchemy engine for the analytics database."""
        global _engine 
        if _engine is None: 
            _engine = create_engine(DATABASE_URL) 
        return _engine