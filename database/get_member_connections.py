import requests

def get_access_token(client_id, client_secret, redirect_uri, code):
    url = "https://discord.com/api/oauth2/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=data, headers=headers)
    return response.json()

def get_user_connections(access_token):
    url = "https://discord.com/api/users/@me/connections"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    return response.json()