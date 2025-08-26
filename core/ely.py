import requests
from ely_device import authorize_via_device_code
from flow import logged
import cfg
BASE_URL = "https://authserver.ely.by"


class AuthError(Exception): pass


@logged
def auth(login, password):
    data = _auth(login, password)
    return {
        "username": data["selectedProfile"]["name"],
        "uuid": data["selectedProfile"]["id"],
        "token": data["accessToken"]
    }

@logged
def _auth(login, password):
    data = {
        "username": login,
        "password": password,
        "clientToken": "tlauncher",
        "requestUser": True
    }
    r = requests.post(BASE_URL + "/auth/authenticate", data=data)
    if r.status_code != 200:
        raise AuthError(r.text)
    return r.json()


@logged
def username(val = None):
    if val is None:
        return cfg.read("../data/login.json")["username"]
    dat = cfg.read("../data/login.json")
    dat["username"] = val
    cfg.write("../data/login.json", dat)


@logged
def uuid(val = None):
    if val is None:
        return cfg.read("../data/login.json")["uuid"]
    dat = cfg.read("../data/login.json")
    dat["uuid"] = val
    cfg.write("../data/login.json", dat)


@logged
def token(val = None):
    if val is None:
        return cfg.read("../data/login.json")["token"]
    dat = cfg.read("../data/login.json")
    dat["token"] = val
    cfg.write("../data/login.json", dat)


@logged
def logged_in(val = None):
    if val is None:
        return cfg.read("../data/login.json")["logged_in"]
    dat = cfg.read("../data/login.json")
    dat["logged_in"] = val
    cfg.write("../data/login.json", dat)

class AuthError(Exception): pass

def auth_device_code():
    """Аутентификация через device code"""
    try:
        token_data = authorize_via_device_code()
        profile = {
            "username": token_data["username"],
            "uuid": token_data.get("uuid", ""),
            "token": token_data["access_token"],
            "logged_in": True
        }
        # Сохраняем данные входа
        write_login_data(profile)
        return profile
    except Exception as e:
        raise AuthError(f"Device code auth failed: {str(e)}")

def write_login_data(data):
    """Сохраняет данные авторизации"""
    login_data = {
        "username": data["username"],
        "uuid": data.get("uuid", ""),
        "token": data["token"],
        "logged_in": data.get("logged_in", False)
    }
    cfg.write("../data/login.json", login_data)

def is_logged_in():
    """Проверяет, есть ли активная сессия"""
    try:
        data = cfg.read("../data/login.json")
        return data.get("logged_in", False)
    except:
        return False

def logout():
    """Выход из системы"""
    write_login_data({
        "username": "",
        "uuid": "",
        "token": "",
        "logged_in": False
    })
    
def auth_password(email, password):
    """Аутентификация через логин/пароль"""
    url = "https://authserver.ely.by/auth/authenticate"
    payload = {
        "username": email,
        "password": password,
        "clientToken": "16Launcher",
        "requestUser": True
    }
    
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        raise AuthError(response.text)
    
    data = response.json()
    return {
        "username": data["selectedProfile"]["name"],
        "uuid": data["selectedProfile"]["id"],
        "token": data["accessToken"]
    }
    
def get_skin_url(username):
    """Получает URL скина пользователя"""
    response = requests.get(f"https://skinsystem.ely.by/skins/{username}.png")
    return response.url if response.status_code == 200 else None

def upload_skin(file_path, token, variant="classic"):
    """
    Загружает скин на Ely.by через официальный API.
    :param file_path: путь к PNG-файлу
    :param token: Bearer-токен Ely.by
    :param variant: 'classic' или 'slim'
    """
    url = "https://account.ely.by/api/resources/skin"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    with open(file_path, 'rb') as f:
        files = {
            'file': ('skin.png', f, 'image/png'),
            'variant': (None, variant)
        }

        response = requests.put(url, headers=headers, files=files)

    if response.status_code == 200:
        return True
    else:
        print("Ошибка загрузки скина:", response.status_code, response.text)
        return False
