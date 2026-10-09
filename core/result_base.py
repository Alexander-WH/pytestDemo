class ResultBase():
    def __init__(self):
        self.success = False
        self.error = None
        self.msg = None
        self.response = None
        self.token = None