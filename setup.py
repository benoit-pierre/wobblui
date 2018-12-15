
from setuptools import setup, Extension, Command
from distutils.command.build_ext import build_ext
from setuptools.command.install import install
from Cython.Build import cythonize
import os
import setuptools

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
                cythonize(full_path,
                    include_path=[os.path.join(os.path.dirname(
                    os.path.abspath(__file__)), "src")],
                )
        super().run()

def extensions():
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
            module = full_path[len(base):].\
                replace(os.path.sep, ".").replace("/", ".")
            if module.endswith(".pyx"):
                module = module[:-len(".pyx")]
            if module.startswith("."):
                module = module[1:]
            if module.endswith("."):
                module = module[:1]
            c_relpath = full_path[len(base):].rpartition(".")[0] + ".c"
            if c_relpath.startswith(os.path.sep):
                c_relpath = c_relpath[1:]
            c_relpath = os.path.join('src', c_relpath)
            result.append(Extension(module, [c_relpath]))
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

if __name__ == "__main__":
    setuptools.setup(
        name="wobblui",
        version=package_version,
        cmdclass={
            "build_ext": cythonize_build_ext_hook},
        author="Jonas Thiem",
        author_email="jonas@thiem.email",
        description="A simple, universal and " +
            "cross-platform UI toolkit for Python 3",
        packages=["wobblui"] + ["wobblui." + p
            for p in setuptools.find_packages("src/wobblui")],
        ext_modules = extensions(),
        package_dir={'':'src'},
        package_data={
            "wobblui": ["font/packaged-fonts/*.ttf",
                "font/packaged-fonts/*.otf",
                "font/packaged-fonts/*.md",
                "font/packaged-fonts/*.txt",
                "img/*.png",
                "*.pxd",
                "font/*.pxd"]
        },
        install_requires=get_requirements_and_dep_links()[0],
        dependency_links=get_requirements_and_dep_links()[1],
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/JonasT/wobblui",
        classifiers=[
            "Programming Language :: Python :: 3",
            "Operating System :: OS Independent",
        ],
    )


