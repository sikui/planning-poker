import cherrypy


class Poll(object):
    @cherrypy.expose
    def index(self):
        return "Hello world!"


if __name__ == '__main__':
    cherrypy.config.update("server.conf")
    cherrypy.quickstart(Poll(), "/polls")