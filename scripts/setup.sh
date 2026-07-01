#! /usr/bin/env bash
# Setup script for using this project.


conda activate
conda activate orchids
poetry env use "$(which python)"
poetry install