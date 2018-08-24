


import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wobblui",
    version="0.0.1",
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


