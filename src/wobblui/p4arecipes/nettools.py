
# A helper recipe for nettools.

from pythonforandroid.recipe import CythonRecipe

class NettoolsRecipe(CythonRecipe):
    version = 'master'
    url = 'https://github.com/JonasT/nettools/archive/{version}.zip'
    depends = ['python3crystax']

recipe = NettoolsRecipe()

