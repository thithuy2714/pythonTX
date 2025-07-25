import hashlib, random, re
from collections import deque
import requests
import math

# + Thống kê toàn cục
total_predictions = 0
correct_count = 0
correct_predictions = {"Tài": 0, "Xỉu": 0}
recent_predictions = deque(maxlen=50)
recent_results = deque(maxlen=50)

# + Thống kê theo cụm prefix MD5 (4 ký tự đầu)
prefix_stats = {}

MD5_RESULT_HISTORY_LEN = 3
sequence_patterns = {}

ALPHA_SMOOTHING = 1
DECAY_FACTOR = 0.95
TOTAL_POSSIBLE_OUTCOMES = 2

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

# --- Hàm mới để cân bằng tác động ---
def get_dynamic_impact_factor():
    if total_predictions == 0:
        return 1.0

    current_accuracy = correct_count / total_predictions
    
    if current_accuracy < 0.5:
        factor = 0.5 + (current_accuracy * 1.0)
    else:
        factor = 1.0 + ((current_accuracy - 0.5) * 1.0)
    
    return max(0.5, min(1.5, factor))

# --- Các Hàm Cốt Lõi ---

def calculate_weighted_likelihoods():
    if not recent_results:
        return {"Tài": 0.5, "Xỉu": 0.5}

    weighted_counts = {"Tài": 0.0, "Xỉu": 0.0}
    total_weighted_sum = 0.0

    for i, result in enumerate(reversed(recent_results)):
        weight = DECAY_FACTOR ** i
        weighted_counts[result] += weight
        total_weighted_sum += weight

    likelihood_tai = (weighted_counts["Tài"] + ALPHA_SMOOTHING) / \
                     (total_weighted_sum + ALPHA_SMOOTHING * TOTAL_POSSIBLE_OUTCOMES)
    likelihood_xiu = (weighted_counts["Xỉu"] + ALPHA_SMOOTHING) / \
                     (total_weighted_sum + ALPHA_SMOOTHING * TOTAL_POSSIBLE_OUTCOMES)

    normalized_total = likelihood_tai + likelihood_xiu
    return {
        "Tài": likelihood_tai / normalized_total,
        "Xỉu": likelihood_xiu / normalized_total
    }

def predict_by_sequence():
    global sequence_patterns
    sequence_length = MD5_RESULT_HISTORY_LEN
    if len(recent_results) < sequence_length:
        return None
    current_sequence = tuple(list(recent_results)[-sequence_length:])
    if current_sequence in sequence_patterns:
        pattern_data = sequence_patterns[current_sequence]
        smoothed_predictions = {}
        total_smoothed_count = 0.0
        for outcome in ["Tài", "Xỉu"]:
            smoothed_predictions[outcome] = pattern_data.get(outcome, 0.0) + ALPHA_SMOOTHING
            total_smoothed_count += smoothed_predictions[outcome]
        if total_smoothed_count > 0:
            tai_prob = smoothed_predictions["Tài"] / total_smoothed_count
            xiu_prob = smoothed_predictions["Xỉu"] / total_smoothed_count
            pattern_confidence_threshold = 0.60
            if tai_prob >= pattern_confidence_threshold:
                return "Tài"
            elif xiu_prob >= pattern_confidence_threshold:
                return "Xỉu"
    return None

def calculate_likelihoods(base_prediction, sequence_prediction):
    likelihoods = {}
    current_weighted_likelihoods = calculate_weighted_likelihoods()
    
    dynamic_factor = get_dynamic_impact_factor()

    # Impact cơ sở mới, nhỏ hơn nhiều so với 0.8 trước đó
    base_md5_impact_magnitude = 0.2
    base_sequence_impact_magnitude = 0.1

    p_tai_base = current_weighted_likelihoods["Tài"]
    p_xiu_base = current_weighted_likelihoods["Xỉu"]

    p_tai_base = max(0.0001, min(0.9999, p_tai_base))
    p_xiu_base = max(0.0001, min(0.9999, p_xiu_base))

    odds_tai_base = p_tai_base / (1 - p_tai_base)
    odds_xiu_base = p_xiu_base / (1 - p_xiu_base)

    md5_adjustment_factor = 1 + (base_md5_impact_magnitude * dynamic_factor)
    
    if base_prediction == "Tài":
        adjusted_odds_tai_md5 = odds_tai_base * md5_adjustment_factor
        adjusted_odds_xiu_md5 = odds_xiu_base / md5_adjustment_factor
    else: 
        adjusted_odds_tai_md5 = odds_tai_base / md5_adjustment_factor
        adjusted_odds_xiu_md5 = odds_xiu_base * md5_adjustment_factor
    
    prob_tai_md5 = adjusted_odds_tai_md5 / (1 + adjusted_odds_tai_md5)
    prob_xiu_md5 = adjusted_odds_xiu_md5 / (1 + adjusted_odds_xiu_md5)

    likelihoods["MD5_Prediction"] = {
        "Tài": max(0.01, min(0.99, prob_tai_md5)),
        "Xỉu": max(0.01, min(0.99, prob_xiu_md5))
    }
    
    total_md5_norm = likelihoods["MD5_Prediction"]["Tài"] + likelihoods["MD5_Prediction"]["Xỉu"]
    if total_md5_norm > 0:
        likelihoods["MD5_Prediction"]["Tài"] /= total_md5_norm
        likelihoods["MD5_Prediction"]["Xỉu"] /= total_md5_norm


    if sequence_prediction is not None:
        # Giới hạn xác suất để tránh lỗi khi chuyển đổi sang odds
        p_tai_seq = current_weighted_likelihoods["Tài"]
        p_xiu_seq = current_weighted_likelihoods["Xỉu"]
        p_tai_seq = max(0.0001, min(0.9999, p_tai_seq))
        p_xiu_seq = max(0.0001, min(0.9999, p_xiu_seq))

        odds_tai_seq = p_tai_seq / (1 - p_tai_seq)
        odds_xiu_seq = p_xiu_seq / (1 - p_xiu_seq)

        sequence_adjustment_factor = 1 + (base_sequence_impact_magnitude * dynamic_factor)

        if sequence_prediction == "Tài":
            adjusted_odds_tai_seq = odds_tai_seq * sequence_adjustment_factor
            adjusted_odds_xiu_seq = odds_xiu_seq / sequence_adjustment_factor
        else: # sequence_prediction == "Xỉu"
            adjusted_odds_tai_seq = odds_tai_seq / sequence_adjustment_factor
            adjusted_odds_xiu_seq = odds_xiu_seq * sequence_adjustment_factor
        
        prob_tai_seq = adjusted_odds_tai_seq / (1 + adjusted_odds_tai_seq)
        prob_xiu_seq = adjusted_odds_xiu_seq / (1 + adjusted_odds_xiu_seq)

        likelihoods["Sequence_Bias"] = {
            "Tài": max(0.01, min(0.99, prob_tai_seq)),
            "Xỉu": max(0.01, min(0.99, prob_xiu_seq))
        }
        total_seq_norm = likelihoods["Sequence_Bias"]["Tài"] + likelihoods["Sequence_Bias"]["Xỉu"]
        if total_seq_norm > 0:
            likelihoods["Sequence_Bias"]["Tài"] /= total_seq_norm
            likelihoods["Sequence_Bias"]["Xỉu"] /= total_seq_norm

    return likelihoods

def analyze_with_bayesian_inference(base_prediction, sequence_prediction):
    prior_probs = calculate_weighted_likelihoods()
    prior_tai = prior_probs["Tài"]
    prior_xiu = prior_probs["Xỉu"]
    evidence_likelihoods = calculate_likelihoods(base_prediction, sequence_prediction)
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
    sequence_prediction = predict_by_sequence()
    if sequence_prediction is not None:
        if sequence_prediction == base_prediction:
            print(f"✅ Dự đoán chuỗi ({sequence_prediction}) TRÙNG với dự đoán MD5 gốc. Tăng độ tin cậy!")
        else:
            print(f"⚠️ Dự đoán chuỗi ({sequence_prediction}) KHÁC với dự đoán MD5 gốc ({base_prediction}).")
    analyze_with_bayesian_inference(base_prediction, sequence_prediction)
    bias_by_prefix(md5_hash)
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

    sequence_length = MD5_RESULT_HISTORY_LEN
    if len(recent_results) > sequence_length:
        pattern_sequence = tuple(list(recent_results)[-sequence_length-1:-1])
        next_result = actual
        if pattern_sequence not in sequence_patterns:
            sequence_patterns[pattern_sequence] = {"Tài": 0.0, "Xỉu": 0.0}
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
        try:
            history_input = input("⌨️ Nhập lịch sử dạng a-b (Tài-Xỉu), ví dụ 12-8, no để bỏ qua ").strip()
        except:
            continue
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
        try:
            md5_hash = input("🔠 Nhập mã MD5: ").strip()
        except:
            continue
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
