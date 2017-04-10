import sys
from subprocess import Popen,PIPE

HOSTS = ['pacifix0','pacifix1','pacifix2',
         'pacifix3','pacifix4','pacifix5',
         'pacifix6','pacifix7','pacifix8',
         'pacifix9','paf0','paf1']

IMAGES = ['reynard:latest',
          'dspsr:cuda8.0',
          'psr-capture:asterix',
          'firmware-control:latest',
          'paf-pipeline:latest']

REPONAME = "docker.mpifr-bonn.mpg.de:5000"

def run(cmd,bg=False):
    print cmd
    proc = Popen(cmd,shell=True,stdout=PIPE,stderr=PIPE)
    return proc

def safe_wait(proc):
    proc.wait()
    out = proc.stdout.read()
    err = proc.stderr.read()
    if "ERROR" in out.upper():
        print out
    if "ERROR" in err.upper():
        print err

def tag(image, repo=REPONAME):
    if image.startswith(repo):
        return image
    tagged = "{repo}/{image}".format(
        image=image,repo=REPONAME)
    cmd = "docker tag {0} {1}".format(
        image,tagged)
    proc = run(cmd)
    proc.wait()
    return tagged

def push(tagged):
    cmd = "docker push {0}".format(tagged)
    return run(cmd)

def deploy(host,tagged):
    cmd = "ssh {host} docker pull {tagged}".format(
        host=host,tagged=tagged)
    return run(cmd)

def main(images,hosts,repo):
    tagged = [tag(image,repo) for image in images]
    for image in tagged:
        proc = push(image)
        proc.wait()
        procs = [deploy(host,image) for host in hosts]
        for proc in procs:
            proc.wait()

if __name__ == "__main__":
    from argparse import ArgumentParser, RawTextHelpFormatter
    usage = "{prog} [options]".format(prog=sys.argv[0])
    parser = ArgumentParser(usage=usage, formatter_class=RawTextHelpFormatter)
    parser.add_argument('-i','--images', nargs='+',
        help='Images to tag and deploy.\nDefaults:\n\t{0}'.format("\n\t".join(IMAGES)),
        default=IMAGES, required=False)
    parser.add_argument('-H','--hosts', nargs='+',
        help='Hosts to deploy to.\nDefaults:\n\t{0}'.format("\n\t".join(HOSTS)),
        default=HOSTS, required=False)
    parser.add_argument('-r','--registry', type=str,
        help='Registry name to tag images with.\nDefault: {0}'.format(REPONAME),
        default=REPONAME, required=False)
    args = parser.parse_args()
    print args
    main(args.images,args.hosts,args.registry)