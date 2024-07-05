from setuptools import setup, find_packages

setup(
    name='agentXNG',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'colorama',
        'pygments',
        'tavily',
        'anthropic',
        'Pillow'
    ],
    entry_points={
        'console_scripts': [
            'agentx=agentx.cli:main',
        ],
    },
)
