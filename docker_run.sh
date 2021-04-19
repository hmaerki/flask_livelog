DOCKER_NAME=flask_livelog

./docker_build.sh

# docker run -it --network host --mount type=bind,source="$(pwd)"/data,target=/home/data $DOCKER_NAME

# docker network create --subnet=10.42.0.0/16 net_zhinst
# docker run -it --network br0 --ip 10.42.0.240 --mount type=bind,source="$(pwd)"/data,target=/data $DOCKER_NAME

docker run --network=host --rm -it -v `pwd`/data:/home/flask_livelog/data -v /var/run/docker.sock:/var/run/docker.sock --name ${DOCKER_NAME} ${DOCKER_NAME}:latest
