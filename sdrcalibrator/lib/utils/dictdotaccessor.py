class DictDotAccessor(object):
    """Allow test profile attributes to be accessed via dot operator"""
    def __init__(self, dct):
        self.__dict__.update(dct)
