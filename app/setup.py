import setuptools

setuptools.setup(
    name="slam",
    version="0.0.1",
    author="Andrew Kwolek",
    author_email="andrewkwolek2025@u.northwestern.edu",
    description="A SLAM implementation using Ping360 Sonar.",
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "fastapi == 0.105.0",
        "anyio == 3.7.1",
        "fastapi-versioning == 0.9.1",
        "loguru == 0.5.3",
        "pyserial == 3.5",
        "starlette == 0.27.0",
        "uvicorn == 0.13.4",
        "requests",
        "pandas==2.1.0",
    ],
)
