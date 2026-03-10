#!/bin/bash

# --- Usage ---
# ./tweet.sh https://koteihi-zero.com/posts/slug
# ./tweet.sh slug --auto
# ./tweet.sh --auto

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
  echo "Error: GEMINI_API_KEY is not set."
  echo "Please set it: export GEMINI_API_KEY='your-key-here'"
  exit 1
fi

# Run the python script with uv to handle dependencies
uv run --with google-generativeai python3 tweet_gen.py "$@"
