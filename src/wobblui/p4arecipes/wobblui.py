
# A recipe file to build wobblui with python-for-android.
# Necessary because we have native Cython components.

from pythonforandroid.recipe import CythonRecipe

class WobbluiRecipe(CythonRecipe):
    version = 'master'
    url = 'https://github.com/JonasT/wobblui/archive/{version}.zip'
    name = 'wobblui'

    depends = ['nettools']

recipe = WobbluiRecipe()

