import cherrypy
import pymysql
import pymysql.cursors
import json
import datetime
import encoder

json_encoder = encoder.JSONEncoder()

def json_handler(*args, **kwargs):
    # Adapted from cherrypy/lib/jsontools.py
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    return json_encoder.iterencode(value)

def CORS():
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "http://localhost"

@cherrypy.popargs('user_id', 'poll_id')
@cherrypy.tools.json_out()
@cherrypy.tools.json_in()
class Vote(object):
    def __init__(self):
        self.possible_votes = [0, 0.5, 1, 2, 3, 5, 8, 13]
        self.mandatory_field = ['value', 'poll_id', 'user_id']

    @cherrypy.expose
    def create_or_edit_vote(self, user_id, poll_id):
        data = cherrypy.request.json
        keys = list(data.keys())
        # TODO: check if user_id and poll_id are valid before inserting
        if poll_id is None:
            cherrypy.response.status = 400
            return {"message" : "Poll ID is missing."}
        try:
            int(poll_id)
        except ValueError:
            cherrypy.response.status = 400
            return {"message": "Invalid Poll ID."}
        if user_id is None:
            cherrypy.response.status = 400
            return {"message" : "User ID is missing."}
        if data.get('value') is None:
            cherrypy.response.status = 400
            return {"message" : "Vote value is missing."}
        try:
            vote = int(data['value'])
            if vote not in self.possible_votes:
                cherrypy.response.status = 400
                return {"message" : "Invalid vote value."}
        except ValueError:
            cherrypy.response.status = 400
            return {"message" : "Vote should be numeric."}
        # create a new vote
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT * FROM votes WHERE user_id = %s AND poll_id = %s",
        [user_id, poll_id])
        exists = c.fetchone()
        if exists is not None :
            c.execute("UPDATE votes SET value= %s WHERE user_id= %s AND poll_id = %s",
            (vote, user_id, poll_id))
        else:
            c.execute("INSERT INTO votes VALUES (%s, %s, %s)",
                (vote, poll_id, user_id))
        return {"message": "The vote has been registerd."}

    @cherrypy.expose
    def poll_user_vote(self, poll_id, user_id):
        if poll_id is None:
            cherrypy.response.status = 400
            return {"data" : "Poll ID is missing."}
        try:
            int(poll_id)
        except ValueError:
            cherrypy.response.status = 400
            return {"data": "Invalid Poll ID."}
        if user_id is None:
            cherrypy.response.status = 400
            return {"data" : "User ID is missing."}
        c = cherrypy.thread_data.db.cursor()
        vote =c.execute("SELECT value FROM votes WHERE user_id=%s AND poll_id = %s",
        (user_id, poll_id))
        value = c.fetchone()
        return {"data" : {"vote": value[0] if value else None}}

@cherrypy.popargs('user_id')
class Users(object):
    def __init__(self):
        pass

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def list_user_polls(self, user_id):
        if user_id is None:
            cherrypy.response.status = 400
            return {"message" : "Missing user id"}
        if user_id.strip() == "":
            cherrypy.response.status = 400
            return {"message" : "User ID cannot be empty."}
        c = cherrypy.thread_data.db.cursor()
        result = c.execute("SELECT * FROM polls WHERE user_id = %ss", (user_id))
        poll_list = list()
        for poll in result.fetchall():
            tmp = dict()
            tmp['id'] = poll[0]
            tmp['title'] = poll[1]
            tmp['description'] = poll[1]
            poll_list.append(tmp)
        return {"polls" : poll_list}


class Poll(object):
    def __init__(self):
        self.mandatory_field = ["title", "description", "created_at", "user_id"]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def create_poll(self):
        data = cherrypy.request.json
        keys = list(data.keys())
        if not all(key in keys for key in self.mandatory_field):
            cherrypy.response.status = 400
            return {"message": "The request is not well formed."}
        if any([value == "" for value in data.values()]) :
            cherrypy.response.status = 400
            return {"message": "Some field in the request are empty."}
        # create a new poll
        conn = cherrypy.thread_data.db
        c = conn.cursor()
        sql = "INSERT INTO `polls` (`title`, `description`, `created_at`, `user_id`) VALUES (%s, %s, %s, %s)"
        try:
            c.execute(sql, (data['title'], data['description'], data['created_at'] , data['user_id']))
            conn.commit()
        except pymysql.err.IntegrityError:
            cherrypy.response.status = 400
            return {"data" : "Poll creation encountered an error."}
        return {"data" : c.lastrowid}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    @cherrypy.popargs('poll_id')
    def edit_poll(self, poll_id):
        data = cherrypy.request.json
        if data.get("id") is None:
            cherrypy.response.status = 400
            return {"message": "Poll ID is not in the request."}
        poll_id = data.get("id")
        data.pop("id")
        update_str = list()
        for key in data.keys():
            update_str.append('SET {}="{}"'.format(key, data[key]))
        conn = cherrypy.thread_data.db
        c = conn.cursor()
        c.execute("UPDATE polls %ss WHERE id = %ss", (','.join(item for item in update_str), poll_id))
        conn.commit()
        return {"message": "Poll correctly modified."}

    @cherrypy.expose
    @cherrypy.tools.json_out(handler=json_handler)
    @cherrypy.popargs('poll_id')
    def polls_details(self, poll_id):
        if poll_id is None:
            cherry.response.status = 400
            return {"message": "Missing poll id in the request."}
        if poll_id.strip() == "":
            cherry.response.status = 400
            return {"message": "Poll ID cannot be empty"}
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT * FROM polls WHERE id = %s", (poll_id))
        poll_details = c.fetchone()
        if poll_details:
            return {"data": {
                            "poll" :{
                                "title" : poll_details['title'],
                                "description" : poll_details['description'],
                                "created_at" : poll_details['created_at']
                                }
                            }
                    }
        else: return {"data" : {"poll" : None}}

def setup_database(threadIndex):
    cherrypy.thread_data.db = pymysql.connect(host='localhost',
                             user='root',
                             password='amicapelosetta',
                             db='poll',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

if __name__ == '__main__':
    cherrypy.engine.subscribe('start_thread', setup_database)
    cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
    d = cherrypy.dispatch.RoutesDispatcher()

    d.connect("default", route="/",
                 controller=Poll(),
                 action='create_poll',
                 conditions=dict(method=['POST']))

    d.connect("default", route="/{poll_id}",
                 controller=Poll(),
                 action='edit_poll',
                 conditions=dict(method=['POST']))

    d.connect("polls_details", route="/{poll_id}",
                 controller=Poll(),
                 action='polls_details',
                 conditions=dict(method=['GET']))


    d.connect("user_polls", route="/users/{user_id}",
                 controller=Users(),
                 action='list_user_polls',
                 conditions=dict(method=['GET']))

    d.connect("user_vote", route="/{poll_id}/users/{user_id}/vote",
                 controller=Vote(),
                 action='create_or_edit_vote',
                 conditions=dict(method=['POST']))

    d.connect("user_votes", route="/{poll_id}/users/{user_id}",
                 controller=Vote(),
                 action='poll_user_vote',
                 conditions=dict(method=['GET']))

    conf = {'/': {
            'request.dispatch': d,
            'tools.CORS.on': True
            }
    }

    cherrypy.tree.mount(Poll(), '/polls', config=conf)
    cherrypy.engine.start()
