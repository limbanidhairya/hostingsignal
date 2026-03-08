"""
HostingSignal CLI Tool — Setup Configuration
Install with: pip install -e . (creates 'hsctl' command)
"""
from setuptools import setup

setup(
    name="hsctl",
    version="1.0.0",
    description="HostingSignal Panel CLI Tool",
    author="HostingSignal",
    author_email="dev@hostingsignal.com",
    py_modules=["hsctl"],
    install_requires=[
        "click>=8.0",
    ],
    entry_points={
        "console_scripts": [
            "hsctl=hsctl:cli",
        ],
    },
    python_requires=">=3.9",
)
