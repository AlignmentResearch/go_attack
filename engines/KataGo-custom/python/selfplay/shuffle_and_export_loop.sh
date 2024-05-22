#!/bin/bash -eu
set -o pipefail
{
if [[ $# -lt 6 ]]
then
    echo "Usage: $0 NAMEPREFIX BASEDIR TMPDIR NTHREADS BATCHSIZE USEGATING USETORCHSCRIPT"
    echo "NAMEPREFIX string prefix for this training run, try to pick something globally unique. Will be displayed to users when KataGo loads the model."
    echo "BASEDIR containing selfplay data and models and related directories"
    echo "TMPDIR scratch space, ideally on fast local disk, unique to this loop"
    echo "NTHREADS number of parallel threads/processes to use in shuffle"
    echo "BATCHSIZE number of samples to concat together per batch for training, must match training"
    echo "USEGATING = 1 to use gatekeeper, 0 to not use gatekeeper"
    echo "USETORCHSCRIPT = 1 to export model as TorchScript, 0 to export as standard KataGo format"
    exit 0
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
. "$SCRIPT_DIR/guess_git_root.sh"

NAMEPREFIX="$1"
shift
BASEDIRRAW="$1"
shift
TMPDIRRAW="$1"
shift
NTHREADS="$1"
shift
BATCHSIZE="$1"
shift
USEGATING="$1"
shift
USETORCHSCRIPT="$1"
shift

basedir="$(realpath "$BASEDIRRAW")"
tmpdir="$(realpath "$TMPDIRRAW")"

mkdir -p "$basedir"/scripts
mkdir -p "$basedir"/logs
cp "$GITROOTDIR"/python/*.py "$GITROOTDIR"/python/selfplay/*.sh "$basedir"/scripts

# For archival and logging purposes - you can look back and see exactly the python code on a particular date
DATE_FOR_FILENAME=$(date "+%Y%m%d-%H%M%S")
DATED_ARCHIVE="$basedir"/scripts/dated/"$DATE_FOR_FILENAME"
mkdir -p "$DATED_ARCHIVE"
cp "$GITROOTDIR"/python/*.py "$GITROOTDIR"/python/selfplay/*.sh "$DATED_ARCHIVE"

(
    cd "$basedir"/scripts
    while true
    do
        ./shuffle.sh "$basedir" "$tmpdir" "$NTHREADS" "$BATCHSIZE" "$@"
        sleep 20
    done
) >> "$basedir"/logs/outshuffle.txt 2>&1 & disown

(
    cd "$basedir"/scripts
    while true
    do
        ./export_model_for_selfplay.sh "$NAMEPREFIX" "$basedir" "$USEGATING" "$USETORCHSCRIPT"
        sleep 10
    done
) >> "$basedir"/logs/outexport.txt 2>&1 & disown

exit 0
}
