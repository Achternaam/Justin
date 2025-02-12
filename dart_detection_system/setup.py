from setuptools import setup, find_packages

setup(
    name="dart_detection_system",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'opencv-python>=4.8.0',
        'numpy>=1.24.0',
        'Pillow>=10.0.0',
    ],
    author="Justin van Uum",
    author_email="j.vanuum@geniusdart.nl",
    description="An automated dart detection and scoring system",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="-",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
