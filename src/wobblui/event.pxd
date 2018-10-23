#cython: language_level=3

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

cdef class Event(object):
    """ CORRESPONDING MEMBER DEFINITION FOR event.pyx's Event CLASS.
        CHECK THERE FOR DOC COMMENT OF HOW THIS CLASS WORKS.
    """
    cdef public object funcs, on_object
    cdef int _disabled
    cdef object special_post_event_func, special_pre_event_func
    cdef public str name
    cdef public int widget_must_get_event


