import random, re
from collections import deque
import requests

# + Thống kê toàn cục
total_predictions = 0
correct_count = 0
correct_predictions = {"Tài": 0, "Xỉu": 0}
recent_predictions = deque(maxlen=20)
recent_results = deque(maxlen=20)

def sum_to_tx(dice):
    return "Tài" if sum(dice) >= 11 else "Xỉu"

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

def predict_chain():
    _ = bias_by_streak()
    return bias_by_winrate()

def predict_smart():
    bias = predict_chain()
    if bias:
        return bias
    dice = [random.randint(1, 6) for _ in range(3)]
    print(f"🎲 Quay xúc xắc: Đang phân tích")
    return sum_to_tx(dice)

def update_accuracy(pred: str, actual: str):
    global total_predictions, correct_count
    total_predictions += 1
    correct = (pred == actual)
    if correct:
        correct_count += 1
        print(f"✅ Đúng ({correct_count}/{total_predictions} - {(correct_count / total_predictions * 100):.2f}%)")
    else:
        print(f"❌ Sai ({correct_count}/{total_predictions} - {(correct_count / total_predictions * 100):.2f}%)")
        print("⚠️ Dự đoán sai, đang tối ưu.")
    correct_predictions[actual] += 1
    recent_predictions.append(pred)
    recent_results.append(actual)
    total = sum(correct_predictions.values())
    print(f"📀 Tài: {(correct_predictions['Tài'] / total * 100):.2f}%")
    print(f"💿 Xỉu: {(correct_predictions['Xỉu'] / total * 100):.2f}%")

def parse_actual_from_code(s: str):
    m = re.search(r'(\d+)-(\d+)-(\d+)', s)
    if m:
        total = sum(map(int, m.groups()))
        return "Tài" if total >= 11 else "Xỉu"
    return None

def parse_initial_history(s: str):
    m = re.fullmatch(r'(\d+)-(\d+)', s)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None

def main():
    
    trying = 0
    
    try:
        print("⚡️ Tool Dự Đoán Tài Xỉu AI ⚡")
        print("🎮 Nhập 'M' để chuyển về chế độ Tài Xỉu MD5, exit out")
        print("❕️Lưu ý mọi kết quả đều là dự đoán.")
        print("🔎 Nhập lịch sử tổng số phiên Tài - Xỉu để khởi tạo phần trăm.")

        while True:
            history_input = input("⌨️ Nhập lịch sử dạng a-b (Tài-Xỉu), ví dụ 12-8, no để bỏ qua ").strip()
            if not history_input:
                continue
            tai, xiu = parse_initial_history(history_input)
            if tai is not None:
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

        while True:
            cmd = input("🔠 Nhập để dự đoán ").strip()
            if not cmd:
                continue
            if cmd.lower() == "exit":
                print("👋 Tạm biệt!")
                break
            if cmd.upper() == "M":
                print("⏳ Đang chuyển sang chế độ MD5...")
                while True:
                    try:
                        md5_code = requests.get("https://raw.githubusercontent.com/baoandepzai/Tool-tai-xiu/refs/heads/main/tooltaixiumd5.py", timeout=5).text
                        exec(md5_code, globals())
                        main()
                        break
                    except Exception as e:
                        if trying == 0:
                            print("❌ Lỗi kết nối mạng. Không thể tải chế độ MD5:", e)
                            trying += 1
                    except Exception as e:
                        if trying == 0:
                            print("❌ Lỗi khác khi tải chế độ MD5:", e)
                            trying += 1

            pred = predict_smart()
            print(f"🎯 Dự đoán: {pred}")
            actual_input = input("🌟 Kết quả thực tế (Tài/Xỉu hoặc a-b-c): ").strip().capitalize()
            if not actual_input:
                continue
            if "-" in actual_input:
                parsed = parse_actual_from_code(actual_input)
                if parsed:
                    update_accuracy(pred, parsed)
                else:
                    print("❗️ Định dạng không hợp lệ.")
            elif actual_input in ["Tài", "Xỉu"]:
                update_accuracy(pred, actual_input)
            else:
                print("❗️ Vui lòng nhập 'Tài', 'Xỉu' hoặc 3 số a-b-c.")
    except Exception as e:
        print("❌ Lỗi không xác định trong chương trình:", e)

if __name__ == "__main__":
    main()
