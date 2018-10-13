
from setuptools import setup, Extension, Command
from distutils.command.build_ext import build_ext
from setuptools.command.install import install
from Cython.Build import cythonize
import os
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("src/wobblui/version.py") as fh:
    contents = fh.read()
    for line in contents.replace("\r\n", "\n").split("\n"):
        if line.replace(" ", "").startswith("VERSION="):
            v = line.partition("=")[2].\
                partition("#")[0].strip()
            if (v.startswith("\"") and v.endswith("\"")) or \
                    (v.startswith("'") or v.endswith("'")):
                v = v[1:-1]
            package_version = v

with open("requirements.txt") as fh:
    dependencies = [l.strip() for l in fh.read().replace("\r\n", "\n").\
        split("\n") if len(l.strip()) > 0]

class force_build_ext_install_hook(install):
    def run(self, *args, **kwargs):
        import subprocess, sys
        subprocess.check_output([sys.executable,
            "setup.py", "build_ext"],
            cwd=os.path.dirname(__file__))
        super().run(*args, **kwargs)

class cythonize_build_ext_hook(build_ext):
    def run(self):
        for root, dirs, files in os.walk(os.path.abspath(
                os.path.join(
                os.path.dirname(__file__), "src"))):
            for f in files:
                if not f.endswith(".pyx"):
                    continue
                full_path = os.path.join(root, f)
                c_path = full_path.rpartition(".")[0] + ".c"
                if os.path.exists(c_path):
                    os.remove(c_path)
                cythonize(full_path)
        super().run()

setuptools.setup(
    name="wobblui",
    version=package_version,
    cmdclass={
        "build_ext": cythonize_build_ext_hook},
    author="Jonas Thiem",
    author_email="jonas@thiem.email",
    description="A simple, universal and " +
        "cross-platform UI toolkit for Python 3",
    packages=setuptools.find_packages("src"),
    ext_modules = [
        Extension("wobblui", ["src/wobblui/__init__.c"]),
        Extension("wobblui.cache", ["src/wobblui/cache.c"]),
        Extension("wobblui.event", ["src/wobblui/event.c"]),
        Extension("wobblui.font.manager", ["src/wobblui/font/manager.c"]),
        Extension("wobblui.font.sdlfont", ["src/wobblui/font/sdlfont.c"]),
        Extension("wobblui.perf", ["src/wobblui/perf.c"]),
        Extension("wobblui.richtext", ["src/wobblui/richtext.c"]),
        Extension("wobblui.widget", ["src/wobblui/widget.c"]),
        Extension("wobblui.widget_base", ["src/wobblui/widget_base.c"]),
        Extension("wobblui.woblog", ["src/wobblui/woblog.c"]),
        ],
    package_dir={'':'src'},
    package_data={
        "wobblui": ["font/packaged-fonts/*.ttf",
            "font/packaged-fonts/*.md",
            "img/*.png"]
    },
    install_requires=dependencies,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JonasT/wobblui",
    data_files = [("", ["LICENSE.md"])],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)


