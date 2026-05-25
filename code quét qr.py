import cv2
import numpy as np
from pyzbar.pyzbar import decode
from pymodbus.client import ModbusTcpClient
import time

# --- 1. CẤU HÌNH VÀ XÁC NHẬN KẾT NỐI PLC ---
PLC_IP = '192.168.0.1' 
# BỔ SUNG: Thêm timeout=1 để khi thử kết nối lại không làm treo/đơ camera quá lâu
client = ModbusTcpClient(PLC_IP, port=502, timeout=1) 

print("--- HỆ THỐNG LƯU KHO TỰ ĐỘNG ---")
print(f"Đang thử kết nối tới PLC tại địa chỉ: {PLC_IP}...")

if client.connect():
    print("SUCCESS: Kết nối PLC THÀNH CÔNG! Hệ thống sẵn sàng.")
else:
    print("CẢNH BÁO: CHƯA THỂ kết nối tới PLC! Chương trình vẫn chạy và sẽ chờ kết nối.")
    # Đã bỏ dòng exit() để code vẫn chạy tiếp dù chưa bật PLC

# --- 2. BIẾN TRẠNG THÁI & HÀM GỬI DỮ LIỆU (ĐÃ SỬA LẠI) ---
last_qr_content = None 

def send_to_plc(value):
    # 1. Nếu mất kết nối -> Cố gắng kết nối lại
    if not client.connected:
        print("--> [PLC] Đang thử kết nối lại với PLC...")
        client.connect()

    # 2. Nếu đã kết nối -> Tiến hành gửi dữ liệu
    if client.connected:
        try:
            result = client.write_register(0, value)
            if not result.isError():
                print(f"--> [PLC] Đã cập nhật ô nhớ: {value}")
            else:
                print("--> [PLC] Lỗi: Gửi dữ liệu thất bại!")
        except Exception as e:
            # Bắt lỗi khi dây cáp bị rút đột ngột ngay đúng lúc đang truyền dữ liệu
            print(f"--> [PLC] Ngoại lệ giao tiếp: {e}")
            client.close() # Đóng kết nối lỗi để chu kỳ sau nó tự kết nối lại
    else:
        print("--> [PLC] Vẫn chưa có kết nối. Bỏ qua lệnh gửi, chờ lần sau.")

# --- 3. VÒNG LẶP XỬ LÝ CHÍNH ---
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 

if not cap.isOpened():
    print("ERROR: Máy tính thấy Index 1 nhưng không lấy được luồng video.")
    exit()

cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)

while True:
    success, frame = cap.read()
    if not success: break
    qr_codes = decode(frame)

    # 1. Không thấy mã QR nào -> Reset trạng thái
    if len(qr_codes) == 0:
        last_qr_content = None 
    
    # 2. Phát hiện NHIỀU HƠN 1 mã QR cùng lúc
    elif len(qr_codes) > 1:
        for code in qr_codes:
            pts = np.array([code.polygon], np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (0, 0, 255), 3) 
            cv2.putText(frame, "LOI: NHIEU QR", (code.rect.left, code.rect.top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        if last_qr_content != "MULTIPLE_QR":
            print(f"\n[CẢNH BÁO] Phát hiện {len(qr_codes)} mã QR cùng lúc trên camera!")
            send_to_plc(98)
            last_qr_content = "MULTIPLE_QR" 
            
    # 3. Chỉ có CHÍNH XÁC 1 mã QR (xử lý bình thường)
    else:
        code = qr_codes[0] 
        content = code.data.decode('utf-8')

        pts = np.array([code.polygon], np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], True, (0, 255, 0), 3)
        cv2.putText(frame, content, (code.rect.left, code.rect.top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        if content != last_qr_content:
            print(f"\n[PHÁT HIỆN] Nội dung mã: {content}")
            last_qr_content = content 

            if content == "mã hàng 1":
                send_to_plc(1)
            elif content == "mã hàng 2":
                send_to_plc(2)
            elif content == "mã hàng 3":
                send_to_plc(3)
            elif content == "mã hàng 4":
                send_to_plc(4)
            else:
                send_to_plc(99) 

    cv2.imshow('DO AN TOT NGHIEP', frame)
    
    if cv2.waitKey(100) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
client.close()
print("\nĐã đóng kết nối và thoát chương trình.")
