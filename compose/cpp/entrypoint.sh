#!/bin/bash

# Set umask to group-writeable, so newly created directories are group-writeable
# by default. Makes it so jobs from CHAI nodes and Hofvarpnir can communicate
# over NFS.
umask 002

# Run the actual command
exec "$@"
