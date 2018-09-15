
'''
wobblui - Copyright 2018 wobblui team, see AUTHORS.md

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
'''

class KeyValueCache(object):
    def __init__(self, size=5000, destroy_func=None):
        self.size = size
        self.destroy_func = destroy_func
        self.clear()        

    def clear(self):
        _got_error = None
        if self.destroy_func != None and \
                hasattr(self, "cache_Key_to_value"):
            for v in self.values:
                try:
                    self.destroy_func(v)
                except Exception as e:
                    _got_error = e
        self.cache_keys = set()
        self.cache_key_to_value = dict()
        self.cache_queries = list()
        if _got_error != None:
            raise _got_error

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
            try:
                if self.destroy_func != None:
                    self.destroy_func(
                        self.cache_key_to_value[self.cache_queries[0]])
            finally:
                try:
                    self.cache_key_to_value.pop(self.cache_queries[0])
                except KeyError:
                    pass
                self.cache_keys.discard(self.cache_queries[0])
                self.cache_queries = self.cache_queries[1:]
        self.cache_key_to_value[key] = value
        self.cache_queries.append(key)
        self.cache_keys.add(key)

