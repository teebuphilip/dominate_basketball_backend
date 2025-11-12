#!/bin/bash
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
REPORT_DIR="reports"
mkdir -p "$REPORT_DIR"
echo "=== Syncing Postman env from config.yaml ==="
python3 sync_env_from_yaml.py || true
echo "=== Running Python Expanded Suite ==="
if [ -d "python_tests/python_tests_expanded/tests" ]; then
  pytest -q python_tests/python_tests_expanded/tests --html=$REPORT_DIR/expanded_$TIMESTAMP.html --self-contained-html || true
fi
echo "=== Running Python Fully Expanded Suite ==="
if [ -d "python_tests/python_tests_fully_expanded/tests" ]; then
  pytest -q python_tests/python_tests_fully_expanded/tests --html=$REPORT_DIR/fully_expanded_$TIMESTAMP.html --self-contained-html || true
fi
echo "=== Running Python All Features Suite ==="
if [ -d "python_tests/python_tests_all_features/tests" ]; then
  pytest -q python_tests/python_tests_all_features/tests --html=$REPORT_DIR/all_features_$TIMESTAMP.html --self-contained-html || true
fi
echo "=== Running Postman (Newman) Collection ==="
if command -v newman >/dev/null 2>&1; then
  newman run postman_collections/full_postman_collection_all_workflows.json -e postman_collections/environment_template.json -r cli,html --reporter-html-export $REPORT_DIR/postman_report_$TIMESTAMP.html || true
else
  echo "Newman is not installed; skipping Postman run"
fi
echo "Reports saved to $REPORT_DIR"
