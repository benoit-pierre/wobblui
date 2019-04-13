'''
wobblui - Copyright 2018-2019 wobblui team, see AUTHORS.md

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

import sys
if int(sys.version.split(".")[0]) < 3:
    raise RuntimeError("python2 is not supported")

import setuptools
from setuptools import setup, Extension, Command
from setuptools.command.build_ext import build_ext
import setuptools.command.build_py
from setuptools.command.install import install
import shutil
import os

with open("README.md", "r") as f:
    with open("LICENSE.md", "r") as f2:
        long_description = f.read().rstrip() + "\n\n" + f2.read()

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


def extensions():
    from Cython.Build import cythonize
    base = os.path.normpath(os.path.abspath(
            os.path.join(
            os.path.dirname(__file__), "src")))
    result = []
    for root, dirs, files in os.walk(base):
        for f in files:
            if not f.endswith(".pyx"):
                continue
            full_path = os.path.normpath(os.path.abspath(
                os.path.join(root, f)))
            assert(full_path.startswith(base))
            pyx_relpath = full_path[len(base):].rpartition(".")[0] + ".pyx"
            if pyx_relpath.startswith(os.path.sep):
                pyx_relpath = pyx_relpath[1:]
            result += cythonize(
                full_path,
                include_path=[os.path.join(os.path.dirname(
                os.path.abspath(__file__)), "src")],
                compiler_directives={
                    'always_allow_keywords': True,
                    'boundscheck': True,
                    'language_level': 3,
                }
            )
    return result


def parse_dependency_url(url):
    package_name = None
    version = None
    fetch_type = None
    branch = None
    if url.startswith("-e "):
        url = url.partition("-e ")[2].lstrip()
    if url.startswith("git+") or (url.find("@") > 0 and
            url.find(" git+") > url.find("@")):
        url = url[url.find("git+"):]
        fetch_type = "git"
    elif url.startswith("https:"):
        fetch_type = "https"
    elif url.find("@") > 0 and url.find("://") > url.find("@"):
        # bla @ <url> format
        package_name = url.partition("@")[0].strip()
        (_, version, url, fetch_type) = \
            parse_dependency_url(url.partition("@")[2].lstrip())
        return (package_name, version, url, fetch_type)
    elif url.find("://") < 0:
        package_name = url
        if package_name.find("==") > 0:
            version = package_name.partition("==")[2]
            package_name = package_name.partition("==")[0]
        return (package_name, version, None, "pip")
    if url.find("@") > 0:
        branch = url.partition("@")[2]
        url = url.partition("@")[0]
        if branch.find("#egg=") > 0:
            url += branch[branch.find("#egg="):]
            branch = branch.partition("#egg=")[0]
    if url.find("#egg=") >= 0:
        if package_name is None:
            package_name = url.partition("#egg=")[2].strip()
            if len(package_name) == 0:
                package_name = None
        url = url.partition("#egg=")[0]
    if package_name != None:
        def is_digit(c):
            if ord(c) >= ord("0") and ord(c) <= ord("9"):
                return True
            return False
        version_part = ""
        i = 0
        while i < len(package_name) - 1:
            if package_name[i] == "-":
                if is_digit(package_name[i + 1]) or \
                        package_name[i:].startswith("-master"):
                    version_part = package_name[i + 1:]
                    package_name = package_name[:i]
                    break
            i += 1
        if len(version_part.strip()) > 0:
            version = version_part
    else:
        if url.find("/tarball/") > 0:
            pname = url[:url.find("/tarball/")]
            if pname.find("/") >= 0:
                pname = pname.rpartition("/")[2]
            package_name = pname
    if version == "master":
        # Not a true version that can be properly checked
        version = None
    return (package_name, version, url, fetch_type)

def get_requirements_and_dep_links():
    dep_links = []
    requirements = []
    for dep in dependencies:
        (package_name, version, url, fetch_type) =\
            parse_dependency_url(dep)
        version_part = "#egg=" + str(package_name)
        if version != None:
            version_part += "-" + version
        fetch_url = url
        if url != None and fetch_type == "git":
            fetch_url = "git+" + fetch_url
        if url != None:
            dep_links.append(fetch_url + version_part)
            if version != None:
                requirements.append(package_name + " @ " + fetch_url + "#egg=" +
                    package_name + "-" + version)
            else:
                requirements.append(package_name + " @ " + fetch_url)
        else:
            if version != None:
                requirements.append(package_name + "==" + version)
            else:
                requirements.append(package_name)
    return (requirements, dep_links)


class BuildPyCommand(setuptools.command.build_py.build_py):
    """ Custom build command to add in license and logo files. """

    ADDITIONAL_FILES = [
        ("../../LICENSE.md", "LICENSE.md"),
    ]

    def run(self):
        setuptools.command.build_py.build_py.run(self)

        src_dir = self.get_package_dir("wobblui")
        build_dir = os.path.join(self.build_lib, "wobblui")
        for f in self.ADDITIONAL_FILES:
            shutil.copyfile(
                os.path.join(src_dir, f[0]),
                os.path.join(build_dir, f[1])
            )


if __name__ == "__main__":
    setuptools.setup(
        name="wobblui",
        version=package_version,
        cmdclass={
            "build_py": BuildPyCommand, 
        },
        author="Jonas Thiem",
        author_email="jonas@thiem.email",
        description="A simple, universal and " +
            "cross-platform UI toolkit for Python 3",
        packages=["wobblui"] + ["wobblui." + p
            for p in setuptools.find_packages("src/wobblui")],
        ext_modules = extensions(),
        package_dir={'':'src'},
        package_data={"wobblui": [
            "font/packaged-fonts/*.ttf",
            "font/packaged-fonts/*.otf",
            "font/packaged-fonts/*.md",
            "font/packaged-fonts/*.txt",
            "img/*.png",
            "*.pxd",
            "font/*.pxd",
            "LICENSE.md",  # in ADDITIONAL_FILES, see above!
        ]},
        install_requires=[
            entry for entry in get_requirements_and_dep_links()[0]
            if "cython" not in entry.lower()
        ],
        setup_requires=[
            entry for entry in get_requirements_and_dep_links()[0]
            if "cython" in entry.lower()
        ],
        dependency_links=get_requirements_and_dep_links()[1],
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/wobblui/wobblui",
        classifiers=[
            "Programming Language :: Python :: 3",
            "Operating System :: OS Independent",
        ],
    )


