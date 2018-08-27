
class KeyValueCache(object):
    def __init__(self, size=5000, destroy_func=None):
        self.size = size
        self.destroy_func = destroy_func
        self.clear()        

    def clear(self):
        if self.destroy_func != None and \
                hasattr(self, "cache_Key_to_value"):
            for v in self.values:
                self.destroy_func(v)
        self.cache_keys = set()
        self.cache_key_to_value = dict()
        self.cache_queries = list()

    @property
    def values(self):
        return self.cache_key_to_value.values()

    def get(self, key):
        if key in self.cache_keys:
            return self.cache_key_to_value[key]
        return None

    def add(self, key, value):
        if key in self.cache_keys:
            return
        if len(self.cache_queries) > self.size:
            if self.destroy_func != None:
                self.destroy_func(self.cache_key_to_value[self.cache_queries[0]])
            del(self.cache_key_to_value[self.cache_queries[0]])
            self.cache_keys.discard(self.cache_queries[0])
            self.cache_queries = self.cache_queries[1:]
        self.cache_key_to_value[key] = value
        self.cache_queries.append(key)
        self.cache_keys.add(key)

