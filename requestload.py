import requests

trying = 0
trying1 = 0
trying2 = 0

def main():
    global trying, trying1, trying2
    while True:
        try:
            version = requests.get("https://raw.githubusercontent.com/baoandepzai/Tool-tai-xiu/refs/heads/main/Ver").text
            print("Latest version:", version)
            trying = 2
            break
        except Exception as e:
            if trying == 0:
                print("Lỗi kết nối mạng!:", e)
                print("Đang thử lại....")
                trying = 1

    print("Xin chào bạn đến với tool dự đoán! 🎲")
    print("Bạn muốn dùng tool nào?")
    print("➤ Nhập '1' để dùng tool DỰ ĐOÁN Tai Xiu MD5")
    print("➤ Nhập '2' để dùng tool DỰ ĐOÁN Tai Xiu (AI tự đoán)")
    print("⚠️Khi nhập để 1 dòng trống sẽ quay lại chọn tool")
    print("➤ Nhập 'exit' để thoát chương trình")

    while True:
        try:
            choice = input(">>> Nhập lựa chọn của bạn (M/T/exit): ").strip().upper()

            if not choice:
                print("Bạn chưa nhập gì cả! Hãy thử lại! :)")
                continue

            if choice == "EXIT":
                print("Tạm biệt! Hẹn gặp lại lần sau nha! 👋")
                break

            elif choice == "1":
                print("Đang tải tool theo mã MD5...")
                while True:
                    try:
                        response = requests.get("https://raw.githubusercontent.com/baoandepzai/Tool-tai-xiu/refs/heads/main/tooltaixiumd5.py", timeout=5)
                        exec_code(response.text, 'tool_md5')
                        break
                    except requests.exceptions.RequestException:
                        if trying1 == 0:
                            print("Lỗi khi chạy tool M")
                            print("Đang thử lại....")
                            trying1 += 1

            elif choice == "2":
                print("Đang tải tool AI tự đoán...")
                while True:
                    try:
                        response = requests.get("https://raw.githubusercontent.com/baoandepzai/Tool-tai-xiu/refs/heads/main/tooltaixiu.py", timeout=5)
                        exec_code(response.text, 'tool_ai')
                        break
                    except requests.exceptions.RequestException:
                        if trying2 == 0:
                            print("Lỗi khi chạy tool T")
                            print("Đang thử lại....")
                            trying2 += 1

            else:
                print("Lựa chọn không hợp lệ! Vui lòng chỉ nhập 'M', 'T' hoặc 'exit' ! >:(")

        except Exception as e:
            print("Có lỗi xảy ra khi nhập! Hãy thử lại!")
            continue

def exec_code(code_text, namespace_name):
    # Tạo namespace riêng cho tool tải về
    tool_env = {"__name__": "__main__"}
    exec(code_text, tool_env)

if __name__ == "__main__":
    main()
