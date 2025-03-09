# from .api.galaxy_life_api import Mobius
from .database import db_connection
from .extensions.mobius import Mobius as NewMobius

mobius = NewMobius(db_connection)
