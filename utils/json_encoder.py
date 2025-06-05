from datetime import datetime
from json import JSONEncoder

class CustomJSONEncoder(JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
