docker run --name reynard-update reynard bash -c "cd /soft/reynard/ ; git pull ; git checkout dev; python setup.py install"
docker commit reynard-update reynard:latest
docker rm reynard-update
