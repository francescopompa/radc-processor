#! /bin/bash

# Initialize our own variables:
rootDir="/data/FNG"
targetDir="test"
duration=20
maxEvents=1000
maxVolume=30000000000
nTimes=4 
totalTime=$((duration * nTimes + 40))
playbook="/home/mnd/Software/radc-processor/scripts/radc_playbook_neutron.txt"
# total time is equal to n_times*duration

OPTIND=1

while getopts ":b:d:t:e:v:" opt; do
  case "$opt" in
    b) 
    rootDir=$OPTARG
    ;;
    d) 
    targetDir=$OPTARG
    ;;
    t) 
    duration=$OPTARG
    ;; 
    e) 
    maxEvents=$OPTARG
    ;;
    v) 
    maxVolume=$OPTARG
    ;;
    n)
    nTimes=$OPTARG
    ;;
  esac
done

shift $((OPTIND-1))

[ "${1:-}" = "--" ] && shift




radc_commander -p $playbook

echo "Taking data with the following options"
echo "Root directory: ${rootDir}"
echo "Target directory: ${targetDir}"
echo "Duration: ${duration} s"
echo "Events in each chunk: ${maxEvents}"
echo "Maximal volume of each chunk: ${maxVolume} B"
echo "Repeated for ${nTimes} times."
echo "Leftovers: $@"
echo "To see the status of data taking, type screen -r run"
echo "To see the status of the slow control, type screen -r slow_control"


screen -dmS slow_control bash -c "slowControl target_root=${rootDir} target_dir=${targetDir};exec bash"
screen -dmS run
screen -r run -p 0 -X stuff $"for i in $(seq 1 $nTimes)\n"
screen -r run -p 0 -X stuff $"do\n"
screen -r run -p 0 -X stuff $"radc_receiver target_root=${rootDir} target_dir=${targetDir} start=True duration=${duration} chunk_max_events=${maxEvents} chunk_max_volume=${maxVolume}\n"
screen -r run -p 0 -X stuff $"done\n"


    




