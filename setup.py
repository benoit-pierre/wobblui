


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
            "font/packaged-fonts/*.txt",
            "img/*.png"]
    },
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JonasT/wobblui",
    data_files = [("", ["LICENSE.md"])],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: zlib/libpng License",
        "License :: OSI Approved :: MIT License",
        "License :: OSI Approved :: BSD License",
        "License :: OSI Approved :: SIL Open Font License",
        "License :: GUST Font License",
        "Operating System :: OS Independent",
    ],
)


