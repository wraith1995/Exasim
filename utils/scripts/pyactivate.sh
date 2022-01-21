#!/usr/bin/env bash
#https://stackoverflow.com/questions/59895/how-can-i-get-the-source-directory-of-a-bash-script-from-within-the-script-itsel
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
owd=`pwd`
cd $SCRIPT_DIR
cd ../..
cd src
cwd=`pwd`
export PYTHONPATH=$cwd:$PYTHONPATH
cd $owd
