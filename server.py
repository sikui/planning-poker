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
        self.possible_votes = ['0', '0.5', '1', '2', '3', '5', '8', '13']
        self.mandatory_field = ['value', 'poll_id', 'user_id']

    @cherrypy.expose
    def create_or_edit_vote(self, user_id, poll_id):
        data = cherrypy.request.json
        keys = list(data.keys())
        # TODO: check if user_id and poll_id are valid before inserting
        if poll_id is None:
            cherrypy.response.status = 400
            return {"error" : "Poll ID is missing."}
        try:
            int(poll_id)
        except ValueError:
            cherrypy.response.status = 400
            return {"error": "Invalid Poll ID."}
        if user_id is None:
            cherrypy.response.status = 400
            return {"error" : "User ID is missing."}
        if data.get('value') is None:
            cherrypy.response.status = 400
            return {"error" : "Vote value is missing."}
        vote = data['value']
        try:
            int(vote)
            if vote not in self.possible_votes:
                cherrypy.response.status = 400
                return {"error" : "Invalid vote value."}
        except ValueError:
            cherrypy.response.status = 400
            return {"error" : "Vote should be numeric."}
        # create a new vote
        conn = cherrypy.thread_data.db
        c = conn.cursor()
        try:
            c.execute("INSERT INTO votes (value, poll_id, user_id) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE value=%s",
                (vote, poll_id, user_id, vote))
            conn.commit()
        except pymysql.err.IntegrityError:
            cherrypy.response.status = 400
            return {"error": "Inserting vote has encountered an error."}
        return {"data": "The vote has been registerd."}

    @cherrypy.expose
    def poll_user_vote(self, poll_id, user_id):
        if poll_id is None:
            cherrypy.response.status = 400
            return {"error" : "Poll ID is missing."}
        try:
            int(poll_id)
        except ValueError:
            cherrypy.response.status = 400
            return {"error": "Invalid Poll ID."}
        if user_id is None:
            cherrypy.response.status = 400
            return {"error" : "User ID is missing."}
        c = cherrypy.thread_data.db.cursor()
        vote =c.execute("SELECT value FROM votes WHERE user_id=%s AND poll_id = %s",
        (user_id, poll_id))
        value = c.fetchone()
        return {"data" : {"vote": value['value'] if value else None}}

    def poll_votes(self,poll_id):
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT value, count(*) as vote FROM votes WHERE poll_id=%s GROUP BY value", poll_id)
        votes = c.fetchall()
        zero_votes = set(self.possible_votes) - set([item['value'] for item in votes])
        for item in zero_votes:
            votes.append({
                'value': item,
                'votes': 0
            })
        return sorted(votes, key=lambda x: float(x['value']))


@cherrypy.popargs('user_id')
class Users(object):
    def __init__(self):
        pass

    @cherrypy.expose
    @cherrypy.tools.json_out(handler=json_handler)
    @cherrypy.tools.json_in()
    def list_user_polls(self, user_id):
        if user_id is None:
            cherrypy.response.status = 400
            return {"error" : "Missing user id"}
        if user_id.strip() == "":
            cherrypy.response.status = 400
            return {"error" : "User ID cannot be empty."}
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT * FROM polls WHERE user_id = %s", (user_id))
        result = c.fetchall()
        return {"data" : {"polls" : result}}


class Poll(object):
    def __init__(self):
        self.mandatory_field = ["title", "description", "created_at", "user_id"]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def create_poll(self):
        data = cherrypy.request.json
        data['created_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        keys = list(data.keys())
        if not all(key in keys for key in self.mandatory_field):
            cherrypy.response.status = 400
            return {"error": "The request is not well formed."}
        if data.get('title') == "":
            cherrypy.response.status = 400
            return {"error": "Some field in the request are empty."}
        # create a new poll
        conn = cherrypy.thread_data.db
        c = conn.cursor()
        sql = "INSERT INTO `polls` (`title`, `description`, `created_at`, `user_id`) VALUES (%s, %s, %s, %s)"
        try:
            c.execute(sql, (data['title'], data['description'], data['created_at'] , data['user_id']))
            conn.commit()
        except pymysql.err.IntegrityError:
            cherrypy.response.status = 400
            return {"error" : "Poll creation encountered an error."}
        return {"data" : c.lastrowid}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    @cherrypy.popargs('poll_id')
    def edit_poll(self, poll_id):
        data = cherrypy.request.json
        data['created_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if poll_id is None:
            cherrypy.response.status = 400
            return {"error": "Poll ID is not in the request."}
        update_str = list()
        for key in data.keys():
            update_str.append('SET {}="{}"'.format(key, data[key]))
        conn = cherrypy.thread_data.db
        c = conn.cursor()
        c.execute("UPDATE polls {} WHERE id = {}".format(','.join(item for item in update_str), poll_id))
        conn.commit()
        return {"message": "Poll correctly modified."}

    @cherrypy.expose
    @cherrypy.tools.json_out(handler=json_handler)
    def polls_list(self):
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT * FROM polls WHERE date(created_at) = CURDATE()")
        return {"data": {"polls": c.fetchall()}}

    @cherrypy.expose
    @cherrypy.tools.json_out(handler=json_handler)
    @cherrypy.popargs('poll_id')
    def polls_details(self, poll_id):
        if poll_id is None:
            cherry.response.status = 400
            return {"error": "Missing poll id in the request."}
        if poll_id.strip() == "":
            cherry.response.status = 400
            return {"error": "Poll ID cannot be empty"}
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT * FROM polls WHERE id = %s", (poll_id))
        poll_details = c.fetchone()
        votes = Vote().poll_votes(poll_id)
        if poll_details:
            return {"data": {
                            "polls" :{
                                "title" : poll_details['title'],
                                "description" : poll_details['description'],
                                "created_at" : poll_details['created_at']
                                },
                                "votes" : votes,
                            }
                    }
        else: return {"data" : {"polls" : None}}

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

    d.connect("polls_list", route="/list/",
                 controller=Poll(),
                 action='polls_list',
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
