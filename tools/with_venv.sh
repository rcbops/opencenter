#!/bin/bash
TOOLS=`dirname $0`
VENV=$TOOLS/../.opencenter-venv
source $VENV/bin/activate && $@
