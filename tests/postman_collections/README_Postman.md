# Postman Collection - DBB Full Workflows
Import `full_postman_collection_all_workflows.json` into Postman or run via Newman.

Example Newman command:
newman run postman_collections/full_postman_collection_all_workflows.json -e postman_collections/environment_template.json -r cli,html --reporter-html-export reports/postman_report.html

Ensure config.yaml is set and run python sync_env_from_yaml.py to sync Postman env.
