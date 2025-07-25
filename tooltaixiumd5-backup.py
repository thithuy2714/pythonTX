import hashlib, random, re
from collections import deque
import requests

# + Thống kê toàn cục
total_predictions = 0
correct_count = 0
correct_predictions = {"Tài": 0, "Xỉu": 0}
recent_predictions = deque(maxlen=20)
recent_results = deque(maxlen=20)

# + Thống kê theo cụm prefix MD5 (4 ký tự đầu)
prefix_stats = {}

def md5_to_number(md5_hash: str) -> list:
    num = int(md5_hash, 16)
    return [(num >> (8 * i)) % 6 + 1 for i in range(3)]

def sum_to_tx(dice):
    return "Tài" if sum(dice) >= 11 else "Xỉu"

def determine_result(md5_hash):
    return sum_to_tx(md5_to_number(md5_hash))

def bias_by_streak():
    if len(recent_results) < 4:
        return None
    last = recent_results[-1]
    streak = 1
    for res in reversed(list(recent_results)[-5:-1]):
        if res == last:
            streak += 1
        else:
            break
    if streak >= 3:
        print(f"⚠️ Đã có {streak} lần {last} liên tiếp. Nên cân nhắc đợi phiên sau.")
    return None

def bias_by_winrate():
    if len(recent_predictions) < 5:
        return None
    win = {"Tài": 0, "Xỉu": 0}
    for pred, actual in zip(recent_predictions, recent_results):
        if pred == actual:
            win[pred] += 1
    if win["Tài"] != win["Xỉu"]:
        return "Tài" if win["Tài"] > win["Xỉu"] else "Xỉu"
    return None

def bias_by_prefix(md5_hash):
    prefix = md5_hash[:4]
    if prefix in prefix_stats:
        data = prefix_stats[prefix]
        if data["Tài"] > data["Xỉu"]:
            print(f"💡 Prefix {prefix} có xu hướng Tài ({data['Tài']} vs {data['Xỉu']})")
        elif data["Xỉu"] > data["Tài"]:
            print(f"💡 Prefix {prefix} có xu hướng Xỉu ({data['Xỉu']} vs {data['Tài']})")
        else:
            print(f"💡 Prefix {prefix} chưa có xu hướng rõ ràng ({data['Tài']} vs {data['Xỉu']})")
    else:
        print(f"💡 Prefix {prefix} chưa từng xuất hiện trước đó.")
    return None

def predict_chain(md5_hash):
    _ = bias_by_streak()
    bias = bias_by_winrate()
    _ = bias_by_prefix(md5_hash)
    return bias

def predict_smart(md5_hash: str) -> str:
    bias = predict_chain(md5_hash)
    if bias is not None:
        return bias
    return determine_result(md5_hash)

def update_accuracy(pred: str, actual: str, md5_hash=None):
    global total_predictions, correct_count
    total_predictions += 1
    correct = (pred == actual)
    if correct:
        correct_count += 1
        correct_predictions[pred] += 1
        recent_predictions.append(pred)
        recent_results.append(actual)
        print(f"✅ Đúng ({correct_count}/{total_predictions} - {(correct_count / total_predictions * 100):.2f}%)")
    else:
        correct_predictions[actual] += 1
        print(f"❌ Sai ({correct_count}/{total_predictions} - {(correct_count / total_predictions * 100):.2f}%)")
        print("⚠️ Dự đoán sai, đang tối ưu.")
    if md5_hash:
        prefix = md5_hash[:4]
        if prefix not in prefix_stats:
            prefix_stats[prefix] = {"Tài": 0, "Xỉu": 0}
        prefix_stats[prefix][actual] += 1
    total = sum(correct_predictions.values())
    print(f"📀 Tài: {(correct_predictions['Tài'] / total * 100):.2f}%")
    print(f"💿 Xỉu: {(correct_predictions['Xỉu'] / total * 100):.2f}%")
    print("🔡 Nhập MD5 tiếp theo hoặc 'exit' để thoát.")

def parse_actual_from_code(s: str):
    m = re.search(r'(\d+)-(\d+)-(\d+)', s)
    if m:
        total = sum(map(int, m.groups()))
        return "Tài" if total >= 11 else "Xỉu"
    return None

def parse_initial_history(s: str):
    m = re.fullmatch(r'(\d+)-(\d+)', s)
    if m:
        tai = int(m.group(1))
        xiu = int(m.group(2))
        return tai, xiu
    return None, None

def main():
    
    trying = 0
    
    print("⚡️ Tool Dự Đoán Tài Xỉu MD5 AI ⚡")
    print("Code made by BaoAn")
    print("🔥Thua tự chịu")
    print("❕️Lưu ý kết quả nhận được đều là sự tính toán")
    print("🔎 Nhập lịch sử tổng số phiên Tài - Xỉu để khởi tạo phần trăm.")
    while True:
        history_input = input("⌨️ Nhập lịch sử dạng a-b (Tài-Xỉu), ví dụ 12-8, no để bỏ qua ").strip()
        tai, xiu = parse_initial_history(history_input)
        if tai is not None and xiu is not None:
            total = tai + xiu
            if total == 0:
                print("❗️ Tổng số phiên phải lớn hơn 0.")
                continue
            print(f"📈 Lịch sử khởi tạo: Tài = {tai} ({tai/total*100:.2f}%), Xỉu = {xiu} ({xiu/total*100:.2f}%)")
            correct_predictions["Tài"] = tai
            correct_predictions["Xỉu"] = xiu
            break
        elif history_input.lower() == "no":
            print("🚪 Bạn đã chọn không nhập lịch sử. Thoát khởi tạo.")
            break
        else:
            print("❗️ Định dạng không đúng, vui lòng nhập lại theo dạng a-b hoặc gõ 'no' để thoát.")

    print("⌨️ Nhập mã MD5 hoặc kết quả a-b-c (vd: 3-4-5) để dự đoán và cập nhật.")
    while True:
        md5_hash = input("🔠 Nhập mã MD5: ").strip()
        if md5_hash.lower() == "exit":
            print("👋 Tạm biệt!")
            break
        if md5_hash.upper() == "T":
            print("⏳ Đang chuyển sang chế độ thường...")
            while True:
                try:
                    md5_code = requests.get("https://raw.githubusercontent.com/baoandepzai/Tool-tai-xiu/refs/heads/main/tooltaixiu.py", timeout = 5).text
                    exec(md5_code, globals())
                    main()
                    break
                except requests.exceptions.RequestException:
                    if trying == 0:
                        print("❌ Lỗi kết nối mạng. Không thể tải chế độ thường.")
                        trying += 1
                except Exception as e:
                    if trying ==0:
                        print("❌ Lỗi khác khi tải chế độ MD5:", e)
                        trying += 1
        if len(md5_hash) != 32 or not re.fullmatch(r'[0-9a-fA-F]{32}', md5_hash):
            print("❗️ Mã MD5 không hợp lệ.")
            continue
        pred = predict_smart(md5_hash)
        print(f"🎯 Dự đoán: {pred}")
        actual_input = input("🌟 Kết quả thực tế (Tài/Xỉu hoặc a-b-c): ").strip().capitalize()
        if "-" in actual_input:
            parsed = parse_actual_from_code(actual_input)
            if parsed:
                update_accuracy(pred, parsed, md5_hash)
            else:
                print("❗️ Không đọc được kết quả.")
        elif actual_input in ["Tài", "Xỉu"]:
            update_accuracy(pred, actual_input, md5_hash)
        else:
            print("❗️ Kết quả không hợp lệ.")

if __name__ == "__main__":
    main()
== "__main__":
    main()
