import sqlite3
from pprint import pprint

from flask import Flask, request, session, g


# Configuration
DATABASE = 'roush.db'
DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('ROUSH_SETTINGS', silent=True)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

@app.route('/role', methods=['GET'])
def list_roles():
    cur = g.db.execute('select id,name,description from roles')
    entries = dict(roles=[dict(role_id=row[0], name=row[1], description=row[2]) for row in cur.fetchall()])
    return '%s' % entries

@app.route('/cluster', methods=['GET'])
def list_roles():
    cur = g.db.execute('select id,name,description from clusters')
    entries = dict(clusters=[dict(role_id=row[0], name=row[1], description=row[2]) for row in cur.fetchall()])
    return '%s' % entries

@app.route('/node', methods=['GET','POST'])
def node():
    if request.method == 'GET':
        cur = g.db.execute('select hostname,role_id,cluster_id from nodes')
        entries = [dict(hostname=row[0], role_id=row[1], cluster_id=row[2]) for row in cur.fetchall()]
        return '%s' % entries
    elif request.method == 'POST':
        g.db.execute('insert into nodes (hostname,role_id,cluster_id) values (?,?,?)', 
                      [request.json['hostname'], request.json['role_id'], request.json['cluster_id']])
        g.db.commit()
        return 'Created new node: %s' % (request.json['hostname'])

@app.route('/node/<node_id>', methods=['GET','PUT','DELETE','PATCH'])
def show_node(node_id):
    if request.method == 'PUT':
        return 'PUT: show_node(%s)' % node_id
    elif request.method == 'PATCH':
        return 'PATCH: show_node(%s)' % node_id
    elif request.method == 'DELETE':
        g.db.execute('delete from nodes where id=%s' % node_id)
        g.db.commit()
        return 'Deleted node: %s' % (node_id)
    elif request.method == 'GET':
        cur = g.db.execute('select hostname,role_id,cluster_id from nodes where id=%s' % node_id)
        entries = [dict(hostname=row[0], role_id=row[1], cluster_id=row[2]) for row in cur.fetchall()]
        return '%s' % entries

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0',port=8080)
