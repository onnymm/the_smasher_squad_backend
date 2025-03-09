import pandas as pd
import numpy as np
from app import db_connection
from datetime import datetime, timedelta
import pytz

def cdxm_now():
    return datetime.now(pytz.timezone('Etc/GMT+6')).replace(tzinfo=None)

def expire_time(seconds: int = 900) -> datetime | None:
    
    def callback(time: datetime | None):
        if time:
            if (cdxm_now() - time).seconds < seconds:
                return time
        return None

    return callback


def get_regeneration_time(s: pd.Series) -> pd.Series:

    # Obtención de la información de la guerra actual
    [ war_info ] = db_connection.search_read('war', fields=['regeneration_hours'], output_format= 'dict')

    # Obtención de las horas de regeneración
    regeneration_hours = war_info['regeneration_hours']

    return s.apply(lambda time: (time + timedelta(hours= regeneration_hours)) if expire_time(regeneration_hours * 3600)(time) else None).replace({np.nan: None})
