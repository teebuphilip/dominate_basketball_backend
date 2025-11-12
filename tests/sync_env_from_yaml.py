import yaml, json, os
yaml_path = "config.yaml"
env_path = "postman_collections/environment_template.json"
with open(yaml_path) as f:
    cfg = yaml.safe_load(f)
if not os.path.exists(env_path):
    raise FileNotFoundError("Postman environment file not found!")
with open(env_path) as f:
    env = json.load(f)
for v in env.get("values", []):
    if v["key"] == "base_url":
        v["value"] = cfg.get("base_url", v["value"])
    elif v["key"] == "api_key":
        v["value"] = cfg.get("api_key", v["value"])
with open(env_path, "w") as f:
    json.dump(env, f, indent=2)
print(f"✅ Postman environment synced with {yaml_path}")
