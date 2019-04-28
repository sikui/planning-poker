import cherrypy
import json
import datetime
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return super().default(obj)
    def iterencode(self, value):
        # Adapted from cherrypy/_cpcompat.py
        for chunk in super().iterencode(value):
            yield chunk.encode("utf-8")
