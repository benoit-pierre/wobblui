
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

def get_requirements_and_dep_links():
    dep_links = []
    requirements = []
    for dep in dependencies:
        if dep.startswith("git+"):
            dep_links.append(dep)
            package_name = dep.partition("egg=")[2].strip()
            if len(package_name) > 0:
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
                "font/packaged-fonts/*.md",
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


