class LLMStrategy:
    def __init__(self, config):
        self.config = config

    def initialize(self):
        raise NotImplementedError("Must implement initialize method")