# vim: tabstop=4 shiftwidth=4 softtabstop=4


class NodeNotFound(Exception):
    message = "Node not found"

    def __init__(self, message=None):
        self.message = message


class CreateError(Exception):
    message = "Generic unable to create error"

    def __init__(self, message=None):
        self.message = message


class AdventureNotFound(Exception):
    message = "Adventure not found"

    def __init__(self, message=None):
        self.message = message


class IdNotFound(Exception):
    message = "Generic ID not found"

    def __init__(self, message=None):
        self.message = message
