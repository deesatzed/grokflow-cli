from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="grokflow-cli",
    version="1.4.0",
    author="GrokFlow Contributors",
    description="Command-line interface for reasoning-amplified development with constraint system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/deesatzed/grokflow-cli",
    packages=find_packages(),
    py_modules=[
        "grokflow",
        "grokflow_v2",
        "grokflow_constraints",
        "grokflow_constraint_cli",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "grokflow=grokflow.cli:main",
            "grokflow-constraint=grokflow_constraint_cli:main",
        ],
    },
)
