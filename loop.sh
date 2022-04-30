#!/bin/bash

for i in {0..100}; do
	echo "*** Iteration ${i} ***"

	output_dir=victimplay-bug-repro/run-${i}
	mkdir -p ${output_dir}
    mv victimplay-bug-repro/active victimplay-bug-repro/active.bak >/dev/null 2>&1
	ln -s run-${i} victimplay-bug-repro/active

	echo "Starting Docker compose"
	docker-compose \
        -f compose/victimplay.yml \
        --env-file compose/victimplay.env \
        up \
        >${output_dir}/compose.stdout \
        2>${output_dir}/compose.stderr&

    wait_time=45
	echo "Waiting for ${wait_time} seconds"
    for i in $(seq $wait_time)
    do
        echo -n .
        sleep 1
    done
    echo -e "\nDone waiting."

	echo "Trying to bring victimplay down now."
	echo "If this hangs, then bug detected!"
	docker-compose -f compose/victimplay.yml --env-file compose/victimplay.env down
	wait
done
