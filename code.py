import requests

trying = 0

while True:
    try:
        exec(requests.get("https://raw.githubusercontent.com/baoandepzai/Tool-tai-xiu/refs/heads/main/requestload.py", timeout = 5).text)
        break
    except requests.exceptions.RequestException:
        if trying == 0:
            print("❗️Lỗi kết nối hãy đang thử lại")
            trying += 1
