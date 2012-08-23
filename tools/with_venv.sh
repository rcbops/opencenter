#!/bin/bash
TOOLS=`dirname $0`
VENV=$TOOLS/../.roush-venv
source $VENV/bin/activate && $@
