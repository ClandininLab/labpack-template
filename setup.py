from setuptools import setup, find_packages

setup(
    name='template_labpack',
    version='1.0.0',
    description='Lab-specific stimuli, protocols and rig configuration to be used with stimpack',
    url='https://github.com/ClandininLab/labpack-template',
    author='Max Turner, Minseung Choi',
    author_email='mhturner@stanford.edu, minseung@stanford.edu',
    # find_packages() so subpackages (protocol, locomotion, visual_stim, ...) are installed too;
    # packages=['template_labpack'] would install only the top-level directory.
    #
    # The package is named template_labpack, not labpack, so that it can be installed alongside a
    # lab's own labpack for comparison. Stimpack never imports this package by name -- it resolves
    # the directory in path_to_labpack.txt and loads modules by file path -- so a lab that forks
    # this repo is free to rename the package to whatever it likes.
    packages=find_packages(),
    python_requires='>=3.10',   # stimpack uses PEP 604 (X | Y) unions at import time
    install_requires=[
        'stimpack',       # the framework this package customizes
        'numpy',
        'scipy',
        'icosphere',      # used by visual_stim/example/shapes.py (GlIcosphere)
    ],
    extras_require={
        # Hardware drivers: only needed on rigs that have that hardware, so not core dependencies.
        'nidaq': ['nidaqmx'],
        'labjack': ['labjack-ljm'],
        'lightcrafter': ['hid'],      # TI DLPC350 projectors, over USB HID
        'test': ['pytest'],
    },
    include_package_data=True,
    zip_safe=False,
)
