docker run --name reynard-update reynard bash -c "cd /soft/reynard/ ; git pull ; python setup.py install"
docker commit reynard-update reynard:latest
docker rm reynard-update