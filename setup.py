from distutils.core import setup
import glob
print(glob.glob('scripts/*'))
setup(name='reynard',
      version='dev',
      packages=['reynard',
                'reynard.monitors',
                'reynard.servers'],
      scripts=['scripts/reynard_basic_cli.py', 
               'scripts/reynard_basic_server.py']
      )
