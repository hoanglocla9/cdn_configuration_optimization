#!/bin/bash
# remove all .pyc from current directory and subdirectories
find . -name \*.pyc -delete
find . -name \*.pkl -delete

rm -rf `find -type d -name .ipynb_checkpoints`
rm -rf data/*
rm -rf DGEMO/result/*
