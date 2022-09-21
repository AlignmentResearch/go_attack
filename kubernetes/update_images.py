"""Automatically build and push new images to Docker Hub if necessary."""

from docker.models.images import Image
import docker
import subprocess


def main():
    client = docker.from_env()
    images = client.images.list(name="humancompatibleai/goattack")

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

    # There's 2 images we care about: {current_hash}-cpp and {current_hash}-python.
    # If either is missing, we need to build and push a new image.
    for image_type in ("cpp", "python"):
        tag = f"{current_hash}-{image_type}"
        if tag in available_tags:
            print(f"Using existing local copy of humancompatibleai/goattack:{tag}")
            continue

        print(f"Building humancompatibleai/goattack:{tag}")
        build_result = client.images.build(
            path=rootdir,
            dockerfile=f"compose/{image_type}/Dockerfile",
            tag=f"humancompatibleai/goattack:{tag}",
        )
        # Pylance can't quite figure out the type of build_result; see
        # https://docker-py.readthedocs.io/en/stable/images.html#image-objects for info
        assert isinstance(build_result, tuple) and len(build_result) == 2
        img, _ = build_result
        assert isinstance(img, Image)
        print(f"Built image {img.short_id} with tags {img.tags}")

        # For some reason we have to explicitly "tag the image in" to the local repo.
        # Otherwise the image doesn't show up in `docker images` and you can't push it.
        # img.tag(repository="humancompatibleai/goattack", tag=tag)
        print(f"Pushing humancompatibleai/goattack:{tag}")
        client.images.push(repository="humancompatibleai/goattack", tag=tag)

    # Write the current image tags to a file so that Kubernetes can use them.
    with open(f"{rootdir}/kubernetes/active-images.env", "w") as f:
        f.write(
            "\n".join(
                [
                    f"CPP_IMAGE=humancompatibleai/goattack:{current_hash}-cpp",
                    f"PYTHON_IMAGE=humancompatibleai/goattack:{current_hash}-python",
                ]
            )
        )


if __name__ == "__main__":
    main()
