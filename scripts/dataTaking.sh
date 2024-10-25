#! /bin/bash

# Initialize our own variables:

killall -u $USER screen

rootDir="/data/DAQMeasurements"
targetDir="test"
duration=180
maxEvents=3000000
maxVolume=500000000
nTimes=10
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

totalTime=$((duration * nTimes))
echo "The measurement will last ${totalTime} s"


screen -dmS slow_control bash -c "slowControl target_root=${rootDir} target_dir=${targetDir};exec bash"
screen -dmS run
screen -r run -p 0 -X stuff $"for i in {1..$nTimes};do radc_receiver target_root=${rootDir} target_dir=${targetDir} start=True duration=${duration} chunk_max_events=${maxEvents} chunk_max_volume=${maxVolume};done\n"


    




