#!/bin/bash

# Push All Script for Albatross
# Usage: ./push_all.sh "Commit message"

COMMIT_MSG=$1

if [ -z "$COMMIT_MSG" ]; then
    echo "Usage: ./push_all.sh \"Your commit message\""
    exit 1
fi

echo "--- Pushing albatross_pro ---"
cd albatross_pro
git add .
git commit -m "$COMMIT_MSG"
git push origin main
cd ..

echo "--- Pushing albatross_docs ---"
cd albatross_docs
git add .
git commit -m "$COMMIT_MSG"
git push origin main
cd ..

echo "--- Pushing Main Core ---"
git add .
git commit -m "$COMMIT_MSG"
git push origin main

echo "All repos updated!"
