from setuptools import setup, find_packages

setup(
    name='labpack',
    version='0.0.1',
    description='Lab-specific stimuli, protocols and rig configuration to be used with stimpack',
    url='https://github.com/ClandininLab/labpack',
    author='Max Turner, Minseung Choi',
    author_email='mhturner@stanford.edu, minseung@stanford.edu',
    # find_packages() so subpackages (protocol, device, visual_stim, ...) are installed too;
    # packages=['labpack'] installed only the top-level directory.
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
    },
    include_package_data=True,
    zip_safe=False,
)
