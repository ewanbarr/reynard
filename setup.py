from distutils.core import setup
import glob
print(glob.glob('scripts/*'))
setup(name='reynard',
      version='dev',
      packages=['reynard',
                'reynard.monitors',
                'reynard.servers',
                'reynard.pipelines',
                'reynard.effelsberg',
                'reynard.effelsberg.paf',
                'reynard.meerkat'],
      scripts=['scripts/reynard_basic_cli.py',
               'scripts/reynard_basic_server.py']
      )
