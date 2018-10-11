
# A helper recipe for nettools.

from pythonforandroid.recipe import CythonRecipe

class Nettools(CythonRecipe):
    version = 'master'
    url = 'https://github.com/JonasT/nettools/archive/{version}.zip'
    name = 'nettools'

    depends = ['nettools']

recipe = WobbluiRecipe()

