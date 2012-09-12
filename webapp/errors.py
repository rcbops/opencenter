#!/usr/bin/env python

from flask import Blueprint, Flask, Response, request
from flask import session, jsonify, url_for, current_app


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


def http_bad_request(error=None):
    msg = {'status': 400,
           'message': "Attribute '%s' was not provided" % error}
    resp = jsonify(msg)
    resp.status_code = 400
    return resp


def http_conflict(error):
    msg = {'status': 409, "message": error.message}
    resp = jsonify(msg)
    resp.status_code = 409
    return resp
