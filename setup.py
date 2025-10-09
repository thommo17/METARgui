from setuptools import setup, find_packages

try:
    from pypandoc import convert

    def read_md(f): return convert(f, 'rst')

except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")

    def read_md(f): return open(f, 'r').read()

###############################################################################

NAME = 'METARgui'
PACKAGES = find_packages()
CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
]

###############################################################################

setup(
    name=NAME,
    version='0.5',
    packages=PACKAGES,
    include_package_data=True,
    description='A web GUI for the Raspberry Pi',
    keywords=['METAR', 'Raspberry Pi'],
    author='Matt Thompson',
    author_email='australianmetarmaps@gmail.com',
    license='MIT',
    classifiers=CLASSIFIERS,
    url='https://github.com/thommo17/METARgui',
    long_description=read_md('README.md'),
    install_requires=open('requirements.txt', 'r').read(),
    entry_points={
        'console_scripts': [
            'rpi_metar = rpi_metar.core:main',
            'rpi_metar_init = rpi_metar.scripts.init:main',
        ],
    },
    python_requires='>=3',
    zip_safe=False,
)
