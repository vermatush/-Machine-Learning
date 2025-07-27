"""
Setup script for KYC PDF Filler package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
else:
    requirements = []

setup(
    name="kyc-pdf-filler",
    version="1.0.0",
    author="KYC PDF Filler Team",
    author_email="contact@example.com",
    description="Automated tool for filling KYC PDF forms from meeting transcripts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/kyc-pdf-filler",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5",
        ],
    },
    entry_points={
        "console_scripts": [
            "kyc-pdf-filler=src.cli:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.json"],
    },
    zip_safe=False,
    keywords="kyc pdf form filling nlp financial advisory",
    project_urls={
        "Bug Reports": "https://github.com/example/kyc-pdf-filler/issues",
        "Source": "https://github.com/example/kyc-pdf-filler",
        "Documentation": "https://kyc-pdf-filler.readthedocs.io/",
    },
)