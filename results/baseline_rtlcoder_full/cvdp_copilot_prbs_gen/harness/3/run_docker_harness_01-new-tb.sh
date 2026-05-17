#!/bin/bash

# Auto-generated script to run harness Docker container
# Usage: run_docker_harness_01-new-tb.sh [-d] (where -d enables debug mode with bash entrypoint)
set -e

# Parse command line arguments
DEBUG_MODE=false
while getopts 'd' flag; do
  case "${flag}" in
    d) DEBUG_MODE=true ;;
  esac
done

# Use shared bridge network: cvdp-bridge-cid003_nonagentic-0272bf87
NETWORK_CREATED=0

# Check if network exists, create if needed
if ! docker network inspect cvdp-bridge-cid003_nonagentic-0272bf87 &>/dev/null; then
  echo "Creating Docker network cvdp-bridge-cid003_nonagentic-0272bf87..."
  docker network create --driver bridge cvdp-bridge-cid003_nonagentic-0272bf87
  NETWORK_CREATED=1
fi

# Function to clean up resources
cleanup() {
  echo "Cleaning up Docker resources..."
  docker compose -f /Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/docker-compose.yml -p cvdp_copilot_prbs_gen_3_1778968830 kill 01-new-tb 2>/dev/null || true
  docker rmi cvdp_copilot_prbs_gen_3_1778968830-01-new-tb 2>/dev/null || true
  if [ $NETWORK_CREATED -eq 1 ]; then
    echo "Removing Docker network cvdp-bridge-cid003_nonagentic-0272bf87..."
    docker network rm cvdp-bridge-cid003_nonagentic-0272bf87 2>/dev/null || true
  fi
}

# Set up cleanup trap
trap cleanup EXIT

# Run the harness container
echo "Running harness with project name: cvdp_copilot_prbs_gen_3_1778968830"
# Get current user and group IDs
USER_ID=$(id -u)
GROUP_ID=$(id -g)

if [ "$DEBUG_MODE" = true ]; then
  echo "DEBUG MODE: Starting container with bash entrypoint"
  docker compose -f /Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/docker-compose.yml -p cvdp_copilot_prbs_gen_3_1778968830 run --rm --user $USER_ID:$GROUP_ID -e HOME=/code/rundir --entrypoint bash -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/docs:/code/docs" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/rundir:/code/rundir" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/rtl:/code/rtl" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/verif:/code/verif" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/src:/code/src" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/src/llm_lib:/pysubj" --rm -w /code/rundir --env OPENAI_USER_KEY=your_openai_api_key_here 01-new-tb
else
  docker compose -f /Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/docker-compose.yml -p cvdp_copilot_prbs_gen_3_1778968830 run --rm --user $USER_ID:$GROUP_ID -e HOME=/code/rundir -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/docs:/code/docs" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/rundir:/code/rundir" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/rtl:/code/rtl" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/verif:/code/verif" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/work_rtlcoder_1sample/cvdp_copilot_prbs_gen/harness/3/src:/code/src" -v "/Users/noahsabbavarapu/Documents/GitHub/spec2RTL/cvdp_benchmark/src/llm_lib:/pysubj" --rm -w /code/rundir --env OPENAI_USER_KEY=your_openai_api_key_here 01-new-tb
fi
exit_code=$?

# Exit with the same code as the docker command
exit $exit_code
