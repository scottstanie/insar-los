import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

# TODO: possible to make compilation from makefile into here?
setuptools.setup(
    name="insar-los",
    version="0.1.0",
    author="Scott Staniewicz",
    author_email="scott.stanie@utexas.com",
    description="Create line of sight maps for InSAR",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/scottstanie/sentineleof",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=(
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: C",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering",
        "Intended Audience :: Science/Research",
    ),
    install_requires=[
        "sentineleof",
        "apertools",
    ],
    entry_points={
        "console_scripts": [
            "create-los-map=create_los_map:main",
        ],
    },
    zip_safe=False,
)
