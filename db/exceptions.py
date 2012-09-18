# vim: tabstop=4 shiftwidth=4 softtabstop=4


class NodeNotFound(Exception):
    message = "Node not found"

    def __init__(self, message=None):
        self.message = message
