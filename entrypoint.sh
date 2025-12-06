#!/bin/sh
set -e

# Run autoheader with the provided arguments
# using sh -c allows arguments passed as a single string to be split
sh -c "autoheader $*"
