import random

# Danh sách proxy IP Việt Nam (HTTP)
VN_PROXIES = [
    "http://113.161.131.69:80",
    "http://103.162.50.14:3128",
    "http://103.160.201.76:10000",
    "http://14.241.225.167:5678"
]

def get_random_proxy():
    return random.choice(VN_PROXIES)

def get_proxy_dict():
    proxy = get_random_proxy()
    return {"http": proxy, "https": proxy}