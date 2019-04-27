import cherrypy
import sqlite3

def CORS():
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "http://localhost"

def db_connect():
    conn = sqlite3.connect('polls.db')
    c = conn.cursor()


@cherrypy.tools.json_out()
@cherrypy.popargs('user_id', 'poll_id')
class Vote(object):
    def __init__(self):
        pass

    @cherrypy.expose
    def create_or_edit_vote(self, user_id, poll_id):
        return {"message": "created vote"}

    @cherrypy.expose
    def poll_user_vote(self, poll_id, user_id):
        return {"message": "list user votes"}

@cherrypy.popargs('user_id')
class Users(object):
    def __init__(self):
        pass

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def list_user_polls(self, user_id):
        return {"message" : "listing user polls"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def poll_user_vote(self):
        return {"message": "list of users vote"}


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
        if not any([value for value in data.values() if value == ""]) :
            cherrypy.response.status = 400
            return {"message": "Some field in the request are empty."}
        return {"message_poll" :"calling post method"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.popargs('poll_id')
    def edit_poll(self, poll_id):
        return {"message": "edit poll"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.popargs('poll_id')
    def polls_details(self, poll_id):
        return {"ciao": "calling get method"}


if __name__ == '__main__':
    db_connect()
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
