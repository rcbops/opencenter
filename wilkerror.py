from flask import request, jsonify
from webapp import Thing

def setup_errors(app):
    @app.errorhandler(404)
    def not_found(error=None):
        msg = {
            'status': 404,
            'message': 'Not Found: ' + request.url}
        resp = jsonify(msg)
        resp.status_code = 404
        return resp
