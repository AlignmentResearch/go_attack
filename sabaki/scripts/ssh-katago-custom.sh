#!/bin/bash
bash_command="/nas/ucb/tony/go-attack/gtp-host/go_attack/sabaki/scripts/docker-katago-custom.sh $@"
echo ${bash_command}
ssh rnn -tt 'bash -l -c "'${bash_command}'"'
