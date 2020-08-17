#/usr/bin/env python3

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

# from flaskr.auth import login_required
from tradeshift.db import get_db

bp = Blueprint('tree', __name__)

nodes = None
root = 1

class Node:
    def __init__(self, pid, level):
        self.parent_id = pid
        self.level = level

def init_cache():
    db = get_db()
    max_id = db.execute('SELECT max(id) as id FROM tree').fetchone()['id']
    global nodes
    global root
    nodes = [None] * (max_id + 1)
    nodes[0] = Node(0, 0)
    rows = db.execute(
        'SELECT id, parent_id'
        ' FROM tree'
    ).fetchall()
    for row in rows:
        if (row['parent_id'] == 0):
            root = row['id']
        par_id = row['parent_id']
        nodes[row['id']] = Node(par_id, 0)
    set_levels(nodes)

def set_levels(nodes):
    changed = True
    while changed:
        changed = False
        for i in range(1, len(nodes)):
            if nodes[i].level != nodes[nodes[i].parent_id].level + 1:
                print("setting level for {:d}".format(i))
                nodes[i].level = nodes[nodes[i].parent_id].level + 1
                changed = True

@bp.route('/')
def index():
    global nodes
    global root
    init_cache()
    res = get_descend_dict(0, nodes, root)
    return render_template('index.html', nodes=res)

def get_children(id, nodes):
    res = []
    for i in range(1, len(nodes)):
        if nodes[i].parent_id == id:            
            res.append((i, id, nodes[i].level))
    return res

def get_descendants(id, nodes):
    print('Searching children of {:d}'.format (id))
    res = []
    newpar = [(id,0,0)]
    found = True
    while found:
        found = False
        parents = newpar
        newpar = []
        for par in parents:
            children = get_children(par[0], nodes)
            print("found children " + ','.join([str(i) for i in children]))
            if (children != []):
                res.extend(children)
                newpar.extend(children)
                found = True
    return res

def get_descend_dict(id, nodes, root):
    res = get_descendants(id, nodes)
    return [{'id':t[0], 'parent_id':t[1], 'root':root, 'level':t[2]} for t in res]

@bp.route('/plain/descendant/<int:id>')
def plain_children(id):
    global nodes
    if nodes == None:
        init_cache()
    res = get_descendants(id, nodes)
    return ', '.join([str(i) for i in res])

@bp.route('/plain/create', methods=('GET', 'POST'))
def plain_create():
    global nodes
    if nodes == None:
        init_cache()
    if request.method == 'POST':
        content = request.get_json()
        node_id = content['id']
        parent_id = content['parent_id']
        error = None
        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO tree(id, parent_id)'
                ' VALUES (?, ?)',
                (node_id, parent_id)
            )
            db.commit()
            while node_id > len(nodes)-1:
                nodes.append(Node(-1, 0))
            nodes.append(Node(parent_id, nodes[parent_id].level+1))
            return 'node {:d} created'.format(node_id)

def do_update(node_id, parent_id, nodes):
    db = get_db()
    db.execute(
        'UPDATE tree '
        'SET parent_id = ? '
        'WHERE id = ?',
        (parent_id, node_id)
    )
    db.commit()
    nodes[node_id].parent_id = parent_id
    nodes[node_id].level = nodes[parent_id].level+1

@bp.route('/plain/update', methods=('GET', 'POST'))
def plain_update():
    if request.method == 'POST':
        content = request.get_json()
        node_id = content['id']
        parent_id = content['parent_id']
        error = None
        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE tree '
                'SET parent_id = ? '
                'WHERE id = ?',
                (parent_id, node_id)
            )
            db.commit()
            nodes[node_id].parent_id = parent_id
            nodes[node_id].level = nodes[parent_id].level+1
            set_levels(nodes)
            return 'parent of {:d} changed to {:d}'.format(node_id, parent_id)

@bp.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')

@bp.route('/descend', methods=('GET', 'POST'))
def descend():
    global nodes
    global root
    if nodes == None:
        init_cache()
    if request.method == 'POST':
        node_id = request.form['node_id']
        res = get_descend_dict(int(node_id), nodes, root)
        return render_template('index.html', nodes=res)
    return render_template('descend.html')

@bp.route('/update', methods=('GET', 'POST'))
def update():
    global nodes
    global root
    if nodes == None:
        init_cache()
    if request.method == 'POST':
        node_id = int(request.form['node_id'])
        parent_id = int(request.form['parent_id'])
        error = None

        if not node_id or not parent_id:
            error = 'Node ID and Parent ID is required.'

        if error is not None:
            flash(error)
        else:
            do_update(node_id, parent_id, nodes)
            res = get_descend_dict(parent_id, nodes, root)
            return render_template('index.html', nodes=res)

    return render_template('update.html')
