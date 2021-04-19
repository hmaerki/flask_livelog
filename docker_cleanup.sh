DOCKER_NAME=flask_livelog

docker container rm --force ${DOCKER_NAME}
docker image rm --force ${DOCKER_NAME}
