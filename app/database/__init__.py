from dml_manager import DMLManager
from app.database.models import Base

db_connection = DMLManager(
    'env',
    Base,
    'dataframe'
)
