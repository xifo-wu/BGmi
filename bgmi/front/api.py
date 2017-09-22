import json
import os
import functools
import tornado.web

from bgmi.config import ADMIN_TOKEN
from bgmi.constants import ACTION_ADD, ACTION_DELETE, ACTION_CAL, ACTION_SEARCH, ACTION_CONFIG, ACTION_DOWNLOAD
from bgmi.controllers import add, delete, search, cal, config
from bgmi.download import download_prepare
from bgmi.front.base import BaseHandler


API_MAP_POST = {
    ACTION_ADD: add,
    ACTION_DELETE: delete,
    ACTION_SEARCH: search,
    ACTION_CONFIG: config,
    ACTION_DOWNLOAD: download_prepare,
}

API_MAP_GET = {
    ACTION_CAL: cal,
    ACTION_CONFIG: lambda: config(None, None)
}

NO_AUTH_ACTION = (ACTION_SEARCH, ACTION_CAL, )


def jsonify(obj):
    return json.dumps(obj, ensure_ascii=False)


def auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if kwargs.get('action', None) in NO_AUTH_ACTION:
            return f(*args, **kwargs)

        if args and isinstance(args[0], BaseHandler):
            token = args[0].request.headers.get('bgmi-token')
            if token == ADMIN_TOKEN:
                return f(*args, **kwargs)

            # maybe return a json
            raise tornado.web.HTTPError(401)
        raise tornado.web.HTTPError(400)

    return wrapper


class ApiHandler(BaseHandler):
    @auth
    def get(self, action, *args, **kwargs):
        if action in API_MAP_GET:
            self.add_header('content-type', 'application/json; charset=utf-8')
            if os.environ.get('DEV', False):
                self.add_header('Access-Control-Allow-Origin', 'http://localhost:8080')
                self.add_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
                self.add_header("Access-Control-Allow-Headers",
                                "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With")
            self.finish(jsonify(API_MAP_GET.get(action)()))

    @auth
    def post(self, action, *args, **kwargs):
        try:
            data = json.loads(self.request.body.decode('utf-8'))
            self.add_header('content-type', 'application/json; charset=utf-8')
            if action in API_MAP_POST:
                if os.environ.get('DEV', False):
                    self.add_header('Access-Control-Allow-Origin', 'http://localhost:8080')
                    self.add_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
                    self.add_header("Access-Control-Allow-Headers",
                                    "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With")
                data = API_MAP_POST.get(action)(**data)
                if data['status'] == 'error':
                    self.set_status(502)
                data = jsonify(data)
                self.finish(data)
                return
            self.write_error(404)
            return
        except json.JSONEncoder:
            self.write_error(502)
            return

    def options(self, *args, **kwargs):
        self.add_header('Access-Control-Allow-Origin', 'http://localhost:8080')
        self.add_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.add_header("Access-Control-Allow-Headers",
                        "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With")
        self.write('')
