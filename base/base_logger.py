import json


class BaseLogger:
    """
    Base class for all logger, including logging on terminal or
    visual plotting.
    """
    def __init__(self):
        self.entries = {}

    def add_entry(self, entry):
        self.entries[len(self.entries) + 1] = entry
    
    def log(self):
        """
        Logging function(print in terminal, plot diagram ...)
        Should be implemented in subclasses
        """
        return NotImplementedError