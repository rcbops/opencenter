#!/bin/bash

function usage {
  echo "Usage: $0 [OPTION]..."
  echo "Run the OpenCenter test suite(s)"
  echo ""
  echo "  -V, --virtual-env        Always use virtualenv.  Install automatically if not present"
  echo "  -N, --no-virtual-env     Don't use virtualenv.  Run tests in local environment"
  echo "  -f, --force              Force a clean re-build of the virtual environment. Useful when dependencies have been added."
  echo "  -p, --pep8               Just run pep8"
  echo "  -c, --coverage           Generate coverage report"
  echo "  -H, --html               Generate coverage report html, if -c"
  echo "  -h, --help               Print this usage message"
  echo "  -F, --full               Run full tests"
  echo ""
  echo "Note: with no options specified, the script will try to run the tests in a virtual environment,"
  echo "      If no virtualenv is found, the script will ask if you would like to create one.  If you "
  echo "      prefer to run tests NOT in a virtual environment, simply pass the -N option."
  exit
}

function process_option {
  case "$1" in
    -h|--help) usage;;
    -V|--virtual-env) always_venv=1; never_venv=0;;
    -N|--no-virtual-env) always_venv=0; never_venv=1;;
    -f|--force) force=1;;
    -F|--full) full=1;;
    -p|--pep8) just_pep8=1;;
    -c|--coverage) coverage=1;;
    -H|--html) html=1;;

    -*) noseopts="$noseopts $1";;
    *) noseargs="$noseargs $1"
  esac
}

venv=.venv
with_venv=tools/with_venv.sh
always_venv=0
never_venv=0
force=0
#no_site_packages=0
# installvenvopts=
noseargs=
noseopts="-v"
wrapper=""
just_pep8=0
coverage=0
html=0


for arg in "$@"; do
  process_option $arg
done

# If enabled, tell nose to collect coverage data
if [ $coverage -eq 1 ]; then
    noseopts="$noseopts --with-coverage --cover-package=opencenter"
fi

function run_tests {
  # cleanup the test database
  if [[ -e test_suite.db ]]; then
    rm -rf test_suite.db
  fi
  # Cleanup *pyc
  ${wrapper} find . -type f -name "*.pyc" -delete
  # Just run the test suites in current environment
  ${wrapper} $NOSETESTS
  RESULT=$?
  if [ "$RESULT" -ne "0" ];
  then
    exit 1
  #  ERRSIZE=`wc -l run_tests.log | awk '{print \$1}'`
  #  if [ "$ERRSIZE" -lt "40" ];
  #  then
  #      cat run_tests.log
  #  fi
  fi
  return $RESULT
}

function run_pep8 {
  echo "Running pep8 ..."
  PEP8_EXCLUDE=".venv"
  PEP8_OPTIONS="--exclude=$PEP8_EXCLUDE --repeat --show-pep8 --show-source"
  PEP8_INCLUDE="."
  ${wrapper} pep8 $PEP8_OPTIONS $PEP8_INCLUDE || exit 1
}

NOSETESTS="nosetests --with-xunit $noseopts $noseargs tests/*test*.py"

if [ ! -z $full ]; then
    NOSETESTS="${NOSETESTS} tests/*full*.py"
fi

if [ $never_venv -eq 0 ]
then
  # Remove the virtual environment if --force used
  if [ $force -eq 1 ]; then
    echo "Cleaning virtualenv..."
    rm -rf ${venv}
  fi
  if [ -e ${venv} ]; then
    wrapper="${with_venv}"
  else
    if [ $always_venv -eq 1 ]; then
      # Automatically install the virtualenv
      env python tools/install_venv.py
      wrapper="${with_venv}"
    else
      echo -e "No virtual environment found...create one? (Y/n) \c"
      read use_ve
      if [ "x$use_ve" = "xY" -o "x$use_ve" = "x" -o "x$use_ve" = "xy" ]; then
        # Install the virtualenv and run the test suite in it
        env python tools/install_venv.py
        wrapper=${with_venv}
      fi
    fi
  fi
fi

# Delete old coverage data from previous runs
if [ $coverage -eq 1 ]; then
    ${wrapper} coverage erase
fi

if [ $just_pep8 -eq 1 ]; then
    run_pep8
    exit
fi

# run_tests || exit
run_tests

if [ $coverage -eq 1 ]; then
    echo "Generating coverage report in coverage/"
    # Don't compute coverage for common code, which is tested elsewhere
    [ $html -eq 1 ] && ${wrapper} coverage html --include='opencenter/*' -d coverage -i
    ${wrapper} coverage xml --include='opencenter/*' -i
fi
