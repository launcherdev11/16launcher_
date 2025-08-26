ELY_CLIENT_ID = "16Launcher"
RELEASE = False
ELY_BY_INJECT = "-javaagent:{}=ely.by"
ELY_BY_INJECT_URL = "https://github.com/yushijinhun/authlib-injector/releases/download/v1.2.5/authlib-injector-1.2.5.jar"

versions = "versions"

import json

def read(path):
    with open(path) as f:
        return json.load(f)

def write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
