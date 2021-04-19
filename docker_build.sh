#
DOCKER_NAME=flask_livelog

docker build -t ${DOCKER_NAME} . --network host
