
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

import threading

cdef class KeyValueCache(object):
    cdef int size
    cdef object destroy_func, mutex
    cdef object cache_keys, cache_key_to_value, cache_queries

    def __init__(self, int size=5000, destroy_func=None):
        self.size = size
        self.destroy_func = destroy_func
        self.mutex = threading.Lock()
        self.clear()        

    def clear(self):
        _got_error = None
        if self.destroy_func != None:
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
        result = None
        self.mutex.acquire()
        if self.cache_key_to_value is None:
            self.cache_keys = dict()
            self.cache_key_to_value = dict()
            self.cache_queries = list()
        result = self.cache_key_to_value.values()
        self.mutex.release()
        return result

    def get(self, object key):
        if not key in self.cache_keys:
            # Without mutex for speed.
            # May race and be wrong, but then it'll just be added
            # to the cache twice which isn't bad.
            return None
        self.mutex.acquire()
        result = None
        if key in self.cache_keys:
            result = self.cache_key_to_value[key]
        self.mutex.release()
        return result

    def add(self, object key, object value):
        self.mutex.acquire()
        if key in self.cache_keys:
            self.mutex.release()
            return
        if len(self.cache_queries) > self.size:
            try:
                if self.destroy_func != None:
                    self.destroy_func(
                        self.cache_key_to_value[self.cache_queries[0]])
            except Exception as e:
                self.mutex.release()
                raise e
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
        self.mutex.release()
