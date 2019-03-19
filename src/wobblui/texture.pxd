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

from libc.stdint cimport uintptr_t


ctypedef int (*_sdl_SetRenderDrawColorType)(void *renderer,
    unsigned char r, unsigned char g, unsigned char b, unsigned char a
) nogil
ctypedef int (*_sdl_RenderCopyType)(
    void *renderer, void *texture, void *rect1, void *rect2
) nogil
ctypedef int (*_sdl_RenderClearType)(
    void *renderer
) nogil
ctypedef int (*_sdl_SetRenderTargetType)(
    void *renderer, void *rt
) nogil
ctypedef void* (*_sdl_GetRenderTargetType)(
    void *renderer
) nogil
ctypedef void (*_sdl_DestroyTextureType)(
    void *texture
) nogil


cdef class Texture:
    cdef object _texture
    cdef uintptr_t texture_address
    cdef public object renderer
    cdef uintptr_t renderer_address
    cdef int width, height
    cdef object __weakref__
    cdef _sdl_SetRenderDrawColorType sdl_func_set_render_draw_color
    cdef _sdl_RenderCopyType sdl_func_render_copy

cdef class RenderTarget(Texture):
    cdef public int set_as_target, ever_rendered_to
    cdef object previous_target

