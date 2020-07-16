#!/bin/bash -e

# keep track of the last executed command
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
# echo an error message before exiting
trap '{ err=$?; if [ $err != 0 ]; then  >&2 echo "ERROR \"${last_command}\" command failed with exit code $err."; fi ; exit $err; } ' EXIT


# This is a test script that populates the output_directory with touched files
output_dir=$2

mkdir -p $output_dir/{Direct1/sub1,Direct2/sub1/sub2,Direct3/sub1/sub2/sub3}

for dir in $output_dir/Direct1/sub1 $output_dir/Direct2/sub1/sub2 $output_dir/Direct3/sub1/sub2/sub3; do
    touch $dir/file.txt
done

echo "add html files to find in $output_dir"
cp /flywheel/v0/output/bids_tree.html $output_dir
cp /flywheel/v0/output/bids_tree.html $output_dir/index.html

if [ -f input/make_me_barf ]; then
    echo "input/make_me_barf exists, so now I generate an error"
    cd no_such_directory
else
    echo "I will not generate an error"
fi

echo "ls "
ls

if [ -f input/skip_echo_sleep ]; then
    echo "Skipping echo-sleep test"
else
    # for t in 1 1 1 1 1 1 1 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 4 ; do
    for t in 1 1 4 ; do
        sleep $(( $t ))
        echo "that was $(( $t )) seconds"
        /bin/date
        echo "this goes to stderr" >&2
    done
fi

echo "test.sh is done"
