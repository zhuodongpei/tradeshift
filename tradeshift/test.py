#!/usr/bin/env python3
from tradeshift import tree

def test():
    from . import db
    db.init_db()
    tree.init_cache()

test()
print(tree.get_child(1))
