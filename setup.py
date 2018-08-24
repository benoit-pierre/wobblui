


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

setuptools.setup(
    name="wobblui",
    version=package_version,
    author="Jonas Thiem",
    author_email="jonas@thiem.email",
    description="A simple, universal and " +
        "cross-platform UI toolkit for Python 3",
    packages=setuptools.find_packages("src"),
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


