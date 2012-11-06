#!/usr/bin/env python

from flask import request, jsonify


def http_not_found(error=None):
    msg = {
        'status': 404,
        'message': 'Not Found: ' + request.url}
    resp = jsonify(msg)
    resp.status_code = 404
    return resp


def http_not_implemented(error=None):
    msg = {
        'status': 501,
        'message': 'Not Implemented'}
    resp = jsonify(msg)
    resp.status_code = 501
    return resp


def http_bad_request(msg):
    msg = {'status': 400,
           'message': msg}
    resp = jsonify(msg)
    resp.status_code = 400
    return resp


def http_conflict(error):
    msg = {'status': 409, "message": error.message}
    resp = jsonify(msg)
    resp.status_code = 409
    return resp
