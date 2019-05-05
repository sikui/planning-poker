import cherrypy
import pymysql
import pymysql.cursors
import json
import datetime
import encoder
import hashlib
import configparser

json_encoder = encoder.JSONEncoder()

def json_handler(*args, **kwargs):
    # Adapted from cherrypy/lib/jsontools.py
    value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
    return json_encoder.iterencode(value)

def CORS():
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "http://localhost"

def error(status,message):
    cherrypy.response.status = status
    return {"error": message}

def read_config():
    config = configparser.ConfigParser()
    config.read('sql_config.ini')
    return config


@cherrypy.popargs('token', 'poll_id')
@cherrypy.tools.json_out()
@cherrypy.tools.json_in()
class Vote(object):
    def __init__(self):
        self.available_votes = {'0', '0.5', '1', '2', '3', '5', '8', '13'}
        self.mandatory_field = ['value', 'poll_id', 'user_id']

    @cherrypy.expose
    def create_or_edit_vote(self, token, poll_id):
        data = cherrypy.request.json
        keys = list(data.keys())
        if poll_id is None:
            return error(400, "Poll ID is missing.")
        try:
            int(poll_id)
        except ValueError:
            return error(400, "Invalid Poll ID.")
        if token is None:
            return error(400, "Token is missing.")
        if data.get('value') is None:
            return error(400, "Vote value is missing.")
        vote = data['value']
        try:
            float(vote)
            if vote not in self.available_votes:
                return error(400, "Invalid vote value.")
        except ValueError:
            return error(400, "Vote should be numeric.")
        # create a new vote
        conn = cherrypy.thread_data.db
        c = conn.cursor()
        try:
            c.execute("INSERT INTO votes (value, poll_id, user_id) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE value=%s",
                (vote, poll_id, token, vote))
            conn.commit()
        except pymysql.err.IntegrityError:
            return error(400, "Inserting vote has encountered an error.")
        return {"data": "The vote has been registerd."}

    @cherrypy.expose
    def poll_user_vote(self, poll_id, token):
        if poll_id is None:
            return error(400, "Poll ID is missing.")
        try:
            int(poll_id)
        except ValueError:
            return error(400, "Invalid Poll ID.")
        if token is None:
            return error(400, "User ID is missing.")
        c = cherrypy.thread_data.db.cursor()
        vote =c.execute("SELECT value FROM votes WHERE user_id=%s AND poll_id = %s",
        (token, poll_id))
        value = c.fetchone()
        return {"data" : {"votes": value['value'] if value else None}}

    def poll_votes(self,poll_id):
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT value, count(*) as votes FROM votes WHERE poll_id=%s GROUP BY value", poll_id)
        votes = list(c.fetchall())
        zero_votes = self.available_votes - set(item['value'] for item in votes)
        for item in zero_votes:
            votes.append({
                'value': item,
                'votes': 0
            })
        return sorted(votes, key=lambda x: float(x['value']))


@cherrypy.popargs('token')
@cherrypy.tools.json_in()
@cherrypy.tools.json_out(handler=json_handler)
class Users(object):

    @cherrypy.expose
    def list_user_polls(self, token):
        if token is None:
            return error(400, "Missing token.")
        if token.strip() == "":
            return error(400, "User ID cannot be empty.")
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT p.id, p.title, p.description, u.username, p.created_at  FROM polls p join users u on p.user_id = u.token WHERE p.user_id = %s", (token))
        result = c.fetchall()
        return {"data" : {"polls" : result}}

    @cherrypy.expose
    def create_user(self):
        data = cherrypy.request.json
        username = data.get('username', None)
        if username is None:
            return error(400, "Missing or empty user name")
        username = username.strip()
        if username == "":
            return error(400, "Username cannot be empty.")
        conn = cherrypy.thread_data.db
        c = conn.cursor()
        token = hashlib.sha256(username.encode('utf-8')).hexdigest()[:32]
        try:
            c.execute("INSERT INTO users (username, token) VALUES (%s,%s)", (username,token))
            conn.commit()
        except pymysql.err.IntegrityError:
            cherrypy.response.status = 400
            return {"error" : "User creation encountered an error."}
        return {"data": {"token": token }}


@cherrypy.popargs('poll_id')
@cherrypy.tools.json_out(handler=json_handler)
@cherrypy.tools.json_in()
class Poll(object):
    def __init__(self):
        self.mandatory_field = ["title", "description", "created_at", "user_id"]

    @cherrypy.expose
    def create_poll(self):
        data = cherrypy.request.json
        data['created_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        keys = list(data.keys())
        if not all(key in keys for key in self.mandatory_field):
            return error(400, "The request is not well formed.")
        if data.get('title') == "":
            return error(400, "Some field in the request are empty.")
        # create a new poll
        conn = cherrypy.thread_data.db
        c = conn.cursor()
        sql = "INSERT INTO `polls` (`title`, `description`, `created_at`, `user_id`) VALUES (%s, %s, %s, %s)"
        try:
            c.execute(sql, (data['title'], data['description'], data['created_at'] , data['user_id']))
            conn.commit()
        except pymysql.err.IntegrityError:
            return error(400, "Poll creation encountered an error.")
        return {"data" : c.lastrowid}

    @cherrypy.expose
    def edit_poll(self, poll_id):
        data = cherrypy.request.json
        if poll_id is None:
            return error(400, "Poll ID is not in the request.")
        update_str = list()
        for key in data.keys():
            update_str.append('SET {}="{}"'.format(key, data[key]))
        conn = cherrypy.thread_data.db
        c = conn.cursor()
        c.execute("UPDATE polls {} WHERE id = {}".format(','.join(item for item in update_str), poll_id))
        conn.commit()
        return {"data": "Poll correctly modified."}

    @cherrypy.expose
    def polls_list(self):
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT p.id, p.title, p.description, u.username, p.created_at  FROM polls p join users u on p.user_id = u.token  WHERE date(created_at) = CURDATE()")
        return {"data": {"polls": c.fetchall()}}

    @cherrypy.expose
    def polls_details(self, poll_id):
        if poll_id is None:
            return error(400, "Missing poll id in the request.")
        if poll_id.strip() == "":
            return error(400, "Poll ID cannot be empty.")
        c = cherrypy.thread_data.db.cursor()
        c.execute("SELECT * FROM polls WHERE id = %s", (poll_id))
        poll_details = c.fetchone()
        votes = Vote().poll_votes(poll_id)
        if poll_details:
            return {"data": {
                            "polls" :poll_details,
                            "votes" : votes,
                            }
                    }
        else:
            return {"data" : {"polls" : None}}

def setup_database(threadIndex):
    sql_config = read_config()
    cherrypy.thread_data.db = pymysql.connect(host=sql_config['database']['host'],
                             user=sql_config['database']['user'],
                             password=sql_config['database']['password'],
                             db=sql_config['database']['db'],
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

    d.connect("user_create", route="/users/create",
                 controller=Users(),
                 action='create_user',
                 conditions=dict(method=['POST']))

    d.connect("user_polls", route="/users/{token}",
                 controller=Users(),
                 action='list_user_polls',
                 conditions=dict(method=['GET']))

    d.connect("user_vote", route="/{poll_id}/users/{token}/vote",
                 controller=Vote(),
                 action='create_or_edit_vote',
                 conditions=dict(method=['POST']))

    d.connect("user_votes", route="/{poll_id}/users/{token}",
                 controller=Vote(),
                 action='poll_user_vote',
                 conditions=dict(method=['GET']))

    conf = {'/': {
            'request.dispatch': d,
            'tools.CORS.on': True,
            'tools.caching.on' : False,
            }
    }

    cherrypy.config.update({'server.thread_pool': 1})
    cherrypy.tree.mount(Poll(), '/polls', config=conf)
    cherrypy.engine.start()
