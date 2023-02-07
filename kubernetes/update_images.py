#!/usr/bin/env python3

"""Automatically build and push new images to Docker Hub if necessary."""

import json
import subprocess
from argparse import ArgumentParser

import docker
from docker.models.images import Image

IMAGE_TYPES = ("cpp", "python", "cpp-and-twogtp")
# Maps an image type X in IMAGE_TYPES to a list of image types that should built
# before X can be built.
IMAGE_PREREQS = {
    "cpp-and-twogtp": ["cpp"],
}
REPO_NAME = "humancompatibleai/goattack"


def main():
    """Main entry point."""
    parser = ArgumentParser(
        description="Builds and pushes new KataGo images to Docker Hub.",
    )
    parser.add_argument(
        "--image",
        type=str,
        choices=IMAGE_TYPES,
        default=["cpp", "python"],
        help="Which images to update",
        nargs="+",
    )
    args = parser.parse_args()
    image_types = args.image

    client = docker.from_env()
    images = client.images.list(name=REPO_NAME)

    # We use the Git hash to tag our images. Find the current hash.
    hash_raw = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
    current_hash = hash_raw.decode("ascii").strip()

    # The "tag" string actually includes the repo name as well
    # (e.g. "humancompatibleai/goattack:c27e251"). These are all
    # from the same repo, so we just look at the tag proper (e.g. "c27e251").
    available_tags = [
        tag.split(":")[1]
        for image in images
        if isinstance(image, Image)
        for tag in image.tags
    ]

    # We also need to know the absolute path for the root Go Attack directory
    # in order to build the Docker images if necessary.
    rootdir_raw = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    rootdir = rootdir_raw.decode("ascii").strip()

    for image_type in image_types:
        tag = f"{current_hash}-{image_type}"
        image_name = f"{REPO_NAME}:{tag}"
        if tag in available_tags:
            print(f"Using existing local copy of {image_name}")
            continue
        # The image is missing, so we need to build and push it.

        BUILD_ARGS = {"ARG_GIT_COMMIT": current_hash}
        prereqs = IMAGE_PREREQS.get(image_type, [])
        for prereq in prereqs:
            print(f"Building prereq: {prereq}")
            client.images.build(
                path=rootdir,
                dockerfile=f"compose/{prereq}/Dockerfile",
                tag=f"{REPO_NAME}:{prereq}",
                buildargs=BUILD_ARGS,
            )
        print(f"Building {REPO_NAME}:{tag}")
        build_result = client.images.build(
            path=rootdir,
            dockerfile=f"compose/{image_type}/Dockerfile",
            tag=image_name,
            buildargs=BUILD_ARGS,
        )
        # Pylance can't quite figure out the type of build_result; see
        # https://docker-py.readthedocs.io/en/stable/images.html#image-objects for info
        assert isinstance(build_result, tuple) and len(build_result) == 2
        img, _ = build_result
        assert isinstance(img, Image)

        print(f"Pushing {image_name}")
        push_result = client.images.push(repository=REPO_NAME, tag=tag)
        # push_result is a string consisting of JSON messages on separate lines
        for line in push_result.splitlines():
            message = json.loads(line)
            if "error" in message:
                raise RuntimeError(f"Pushing {image_name} failed: {message['error']}")

    # Write the current image tags to a file so that Kubernetes can use them.
    with open(f"{rootdir}/kubernetes/active-images.env", "w") as f:
        for image_type in image_types:
            env_variable_name = f"{image_type.upper().replace('-', '_')}_IMAGE"
            f.write(f"{env_variable_name}={REPO_NAME}:{current_hash}-{image_type}\n")


if __name__ == "__main__":
    main()
