FROM circleci/runner:launch-agent as launch-agent

FROM humancompatibleai/goattack:cpp-build-deps as cpp-build-deps
# Drawing from https://github.com/CircleCI-Public/circleci-runner-docker/blob/main/launch-agent/Dockerfile
# Copying over files we can from that Docker image.
# Where we can't, duplicating commands.
RUN apt-get update -q && apt-get install -y gzip apt-transport-https jq && rm -rf /var/lib/apt/lists/*

ARG UID=1500
ARG GID=1500

RUN addgroup --gid ${GID} circleci && \
    adduser --uid ${UID} --ingroup circleci --disabled-password --gecos GECOS circleci
RUN echo "DEBIAN_FRONTEND=noninteractive" > /etc/environment

USER circleci

COPY --from=launch-agent /opt/ /opt/
COPY --from=launch-agent /etc/sudoers.d/circleci/ /etc/sudoers.d/circleci

ENTRYPOINT ["/opt/circleci/start.sh"]
