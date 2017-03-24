from distutils.core import setup
import glob

setup(name='reynard',
    version='dev',
    packages=['reynard',
              'reynard.monitors',
              'reynard.servers',
              'reynard.pipelines',
              'reynard.effelsberg',
              'reynard.effelsberg.servers',
              'reynard.meerkat'],
    scripts=['scripts/reynard_basic_cli.py',
             'scripts/reynard_basic_server.py',
             'scripts/effelsberg/reynard_effcam_server.py'],
    package_data = {
        "reynard":['config/*']
    }
)
