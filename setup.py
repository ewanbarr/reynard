from setuptools import setup
import glob

setup(name='reynard',
    version='0.1',
    description='Controller for pulsar backends',
    author='Ewan Barr',
    author_email='ebarr@mpifr-bonn.mpg.de',
    license='MIT',
    packages=['reynard',
              'reynard.monitors',
              'reynard.servers',
              'reynard.pipelines',
              'reynard.effelsberg',
              'reynard.effelsberg.servers',
              'reynard.meerkat'],
    scripts=['scripts/reynard_basic_cli.py',
             'scripts/reynard_basic_server.py',
             'scripts/reynard_ubi_server.py',
             'scripts/reynard_ubn_server.py',
             'scripts/effelsberg/reynard_effcam_server.py',
             'scripts/effelsberg/reynard_eff_status_server.py'],
    package_data = {
        "reynard":['config/*']
    },
    include_package_data=True,
    zip_safe=False
)
