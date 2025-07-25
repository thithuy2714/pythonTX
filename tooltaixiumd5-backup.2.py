import hashlib, random, re
from collections import deque
import requests

# + Thống kê toàn cục
total_predictions = 0 
correct_count = 0 
correct_predictions = {"Tài": 0, "Xỉu": 0} 

recent_predictions = deque(maxlen=50) 
recent_results = deque(maxlen=50)

# + Thống kê theo cụm prefix MD5 (4 ký tự đầu)
prefix_stats = {}

# Thêm biến toàn cục cho thuật toán phân tích chuỗi
MD5_RESULT_HISTORY_LEN = 3 
sequence_patterns = {} 

def md5_to_number(md5_hash):
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
    if len(recent_results) < 30: 
        return None
    
    tai_count = recent_results.count("Tài")
    xiu_count = recent_results.count("Xỉu")
    total_recent = tai_count + xiu_count

    if total_recent == 0:
        return None

    tai_ratio = tai_count / total_recent
    xiu_ratio = xiu_count / total_recent

    threshold = 0.60 
    
    if tai_ratio >= threshold:
        print(f"💡 Trong {total_recent} ván gần đây (Tài: {tai_count}, Xỉu: {xiu_count}): Tài chiếm {tai_ratio:.2%}. Đang bias Tài.")
        return "Tài"
    elif xiu_ratio >= threshold:
        print(f"💡 Trong {total_recent} ván gần đây (Tài: {tai_count}, Xỉu: {xiu_count}): Xỉu chiếm {xiu_ratio:.2%}. Đang bias Xỉu.")
        return "Xỉu"
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

# Thuật toán phân tích mẫu chuỗi kết quả (Sequence Analysis)
def predict_by_sequence():
    global sequence_patterns 

    sequence_length = MD5_RESULT_HISTORY_LEN 
    
    if len(recent_results) < sequence_length:
        return None 

    current_sequence = tuple(list(recent_results)[-sequence_length:])
    
    if current_sequence in sequence_patterns:
        pattern_data = sequence_patterns[current_sequence]
        total_occurrences = sum(pattern_data.values())
        
        if total_occurrences > 0:
            tai_freq = pattern_data.get("Tài", 0) / total_occurrences
            xiu_freq = pattern_data.get("Xỉu", 0) / total_occurrences
            
            pattern_confidence_threshold = 0.70 

            if tai_freq >= pattern_confidence_threshold:
                print(f"✨Chuỗi kết quả {current_sequence} có xu hướng Tài ({tai_freq:.2%}).")
                return "Tài"
            elif xiu_freq >= pattern_confidence_threshold:
                print(f"✨Chuỗi kết quả {current_sequence} có xu hướng Xỉu ({xiu_freq:.2%}).")
                return "Xỉu"
    return None

# Thuật toán tính toán Likelihood cho Bayesian Inference
def calculate_likelihoods(
    base_prediction, 
    winrate_bias, 
    sequence_prediction
):
    likelihoods = {}

    total_tx_actual = sum(correct_predictions.values())
    tai_ratio_actual = correct_predictions["Tài"] / total_tx_actual if total_tx_actual > 0 else 0.5
    
    md5_bonus_match = 0.08 
    md5_penalty_mismatch = 0.08

    if base_prediction == "Tài":
        likelihood_tai_md5 = tai_ratio_actual + md5_bonus_match
        likelihood_xiu_md5 = (1 - tai_ratio_actual) - md5_penalty_mismatch
    else: 
        likelihood_tai_md5 = tai_ratio_actual - md5_penalty_mismatch
        likelihood_xiu_md5 = (1 - tai_ratio_actual) + md5_bonus_match
    
    likelihoods["MD5_Prediction"] = {
        "Tài": max(0.01, min(0.99, likelihood_tai_md5)),
        "Xỉu": max(0.01, min(0.99, likelihood_xiu_md5))
    }

    winrate_bias_impact = 0.03 

    if winrate_bias is not None:
        if winrate_bias == "Tài":
            likelihoods["Winrate_Bias"] = {
                "Tài": tai_ratio_actual + winrate_bias_impact,
                "Xỉu": (1 - tai_ratio_actual) - winrate_bias_impact
            }
        else: # winrate_bias == "Xỉu"
            likelihoods["Winrate_Bias"] = {
                "Tài": tai_ratio_actual - winrate_bias_impact,
                "Xỉu": (1 - tai_ratio_actual) + winrate_bias_impact
            }
        likelihoods["Winrate_Bias"]["Tài"] = max(0.01, min(0.99, likelihoods["Winrate_Bias"]["Tài"]))
        likelihoods["Winrate_Bias"]["Xỉu"] = max(0.01, min(0.99, likelihoods["Winrate_Bias"]["Xỉu"]))


    sequence_bias_impact = 0.03 

    if sequence_prediction is not None:
        if sequence_prediction == "Tài":
            likelihoods["Sequence_Bias"] = {
                "Tài": tai_ratio_actual + sequence_bias_impact,
                "Xỉu": (1 - tai_ratio_actual) - sequence_bias_impact
            }
        else: # sequence_prediction == "Xỉu"
            likelihoods["Sequence_Bias"] = {
                "Tài": tai_ratio_actual - sequence_bias_impact,
                "Xỉu": (1 - tai_ratio_actual) + sequence_bias_impact
            }
        likelihoods["Sequence_Bias"]["Tài"] = max(0.01, min(0.99, likelihoods["Sequence_Bias"]["Tài"]))
        likelihoods["Sequence_Bias"]["Xỉu"] = max(0.01, min(0.99, likelihoods["Sequence_Bias"]["Xỉu"]))

    return likelihoods

# Thuật toán nhánh phân tích Bayesian Inference độc lập
def analyze_with_bayesian_inference(
    base_prediction, 
    winrate_bias, 
    sequence_prediction
):
    total_tx = sum(correct_predictions.values())
    # Xác suất tiên nghiệm (Prior) lấy từ tỷ lệ Tài/Xỉu trong toàn bộ lịch sử
    prior_tai = correct_predictions["Tài"] / total_tx if total_tx > 0 else 0.5
    prior_xiu = correct_predictions["Xỉu"] / total_tx if total_tx > 0 else 0.5

    evidence_likelihoods = calculate_likelihoods(base_prediction, winrate_bias, sequence_prediction)

    # Tính toán xác suất hậu nghiệm (Posterior)
    posterior_tai = prior_tai
    posterior_xiu = prior_xiu

    for likelihood_values in evidence_likelihoods.values():
        posterior_tai *= likelihood_values["Tài"] 
        posterior_xiu *= likelihood_values["Xỉu"] 

    total_posterior = posterior_tai + posterior_xiu
    if total_posterior == 0:
        final_prob_tai = 0.5
        final_prob_xiu = 0.5
    else:
        final_prob_tai = posterior_tai / total_posterior
        final_prob_xiu = posterior_xiu / total_posterior

    bayesian_result = "Tài" if final_prob_tai >= final_prob_xiu else "Xỉu"
    
    print(f"✨Xác xuất: {bayesian_result} (Tài: {final_prob_tai:.2%}, Xỉu: {final_prob_xiu:.2%})")


def predict_smart(md5_hash):
    base_prediction = determine_result(md5_hash)
    print(f"🎯 Dự đoán: {base_prediction}")

    bias_by_streak()

    winrate_bias = bias_by_winrate()

    if winrate_bias is not None:
        if winrate_bias == base_prediction:
            print(f"✅ Bias Tỷ lệ Thắng ({winrate_bias}) TRÙNG với dự đoán.")
        else:
            print(f"⚠️ Bias Tỷ lệ Thắng ({winrate_bias}) có biến động ({base_prediction}).")
            
    sequence_prediction = predict_by_sequence()
    if sequence_prediction is not None:
        if sequence_prediction == base_prediction:
            print(f"✅ Dự đoán chuỗi ({sequence_prediction}) TRÙNG với dự đoán MD5 gốc. Tăng độ tin cậy!")
        else:
            print(f"⚠️ Dự đoán chuỗi ({sequence_prediction}) KHÁC với dự đoán MD5 gốc ({base_prediction}).")

    analyze_with_bayesian_inference(base_prediction, winrate_bias, sequence_prediction)
    
    bias_by_prefix(md5_hash)

    if winrate_bias is not None:
        return base_prediction 
    
    return base_prediction

def update_accuracy(pred, actual, md5_hash=None):
    global total_predictions, correct_count, correct_predictions, sequence_patterns
    
    total_predictions += 1 
    correct = (pred == actual)
    if correct:
        correct_count += 1 
    
    accuracy_percentage = (correct_count / total_predictions * 100) if total_predictions > 0 else 0.00
    
    if correct:
        print(f"✅ Đúng ({correct_count}/{total_predictions} - {accuracy_percentage:.2f}%)")
    else:
        print(f"❌ Sai ({correct_count}/{total_predictions} - {accuracy_percentage:.2f}%)")
        print("⚠️ Dự đoán sai, đang tối ưu.")

    correct_predictions[actual] += 1
    recent_predictions.append(pred)
    recent_results.append(actual)

    # Cập nhật các mẫu chuỗi kết quả (dùng cho predict_by_sequence)
    sequence_length = MD5_RESULT_HISTORY_LEN
    if len(recent_results) > sequence_length:
        pattern_sequence = tuple(list(recent_results)[-sequence_length-1:-1])
        next_result = actual 

        if pattern_sequence not in sequence_patterns:
            sequence_patterns[pattern_sequence] = {"Tài": 0, "Xỉu": 0}
        sequence_patterns[pattern_sequence][next_result] += 1

    if md5_hash:
        prefix = md5_hash[:4]
        if prefix not in prefix_stats:
            prefix_stats[prefix] = {"Tài": 0, "Xỉu": 0}
        prefix_stats[prefix][actual] += 1
    
    total_tx_actual = sum(correct_predictions.values())
    if total_tx_actual > 0:
        tai_percent = (correct_predictions['Tài'] / total_tx_actual * 100)
        xiu_percent = (correct_predictions['Xỉu'] / total_tx_actual * 100)
        print(f"📀 Tài: {tai_percent:.2f}%")
        print(f"💿 Xỉu: {xiu_percent:.2f}%")
    else:
        print("📀 Tài: 0.00%")
        print("💿 Xỉu: 0.00%")
        
    print("🔡 Nhập MD5 tiếp theo hoặc 'exit' để thoát.")

def parse_actual_from_code(s):
    m = re.search(r'(\d+)-(\d+)-(\d+)', s)
    if m:
        total = sum(map(int, m.groups()))
        return "Tài" if total >= 11 else "Xỉu"
    return None

def parse_initial_history(s):
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
            total_history = tai + xiu 
            if total_history == 0:
                print("❗️ Tổng số phiên phải lớn hơn 0.")
                continue
            print(f"📈 Lịch sử khởi tạo: Tài = {tai} ({tai/total_history*100:.2f}%), Xỉu = {xiu} ({xiu/total_history*100:.2f}%)")
            
            global correct_predictions
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
            continue
        
        if len(md5_hash) != 32 or not re.fullmatch(r'[0-9a-fA-F]{32}', md5_hash):
            print("❗️ Mã MD5 không hợp lệ.")
            continue
            
        pred = predict_smart(md5_hash)
        
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