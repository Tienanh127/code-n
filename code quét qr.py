import cv2
import numpy as np
from pyzbar.pyzbar import decode
from pymodbus.client import ModbusTcpClient
import time

# --- 1. CẤU HÌNH VÀ XÁC NHẬN KẾT NỐI PLC ---
PLC_IP = '192.168.0.1' # IP mặc định hoặc IP bạn đã đặt cho S7-1200
client = ModbusTcpClient(PLC_IP, port=502)

print("--- HỆ THỐNG PHÂN LOẠI HÀNG HÓA - TIẾN ANH HUST ---")
print(f"Đang thử kết nối tới PLC tại địa chỉ: {PLC_IP}...")

# Cố gắng kết nối
if client.connect():
    print("SUCCESS: Kết nối PLC THÀNH CÔNG! Hệ thống sẵn sàng.")
else:
    print("ERROR: KHÔNG THỂ kết nối tới PLC!")
    print("Vui lòng kiểm tra:")
    print(" 1. Dây cáp mạng LAN.")
    print(" 2. IP tĩnh của Laptop (phải cùng lớp 192.168.0.x).")
    print(" 3. Khối MB_SERVER đã được nạp xuống PLC chưa.")
    # Bạn có thể chọn thoát chương trình nếu không có kết nối
    # exit() 

# --- 2. BIẾN TRẠNG THÁI & HÀM GỬI DỮ LIỆU ---
last_qr_content = None 

def send_to_plc(value):
    if client.connected:
        result = client.write_register(0, value) # Ghi vào Holding_Registers[0]
        if not result.isError():
            print(f"--> [PLC] Đã cập nhật ô nhớ: {value}")
        else:
            print("--> [PLC] Gửi dữ liệu thất bại!")
    else:
        print("--> [PLC] Cảnh báo: Mất kết nối PLC giữa chừng!")

# --- 3. VÒNG LẶP XỬ LÝ CHÍNH ---
cap = cv2.VideoCapture(0)
# Thử dùng backend CAP_DSHOW để Windows nhận diện nhanh hơn
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 

# Kiểm tra xem camera có thực sự mở được không
if not cap.isOpened():
    print("ERROR: Máy tính thấy Index 1 nhưng không lấy được luồng video.")
    print("Hãy kiểm tra xem app Camera của Windows có đang mở không (nếu có thì phải tắt đi).")
    exit()

# Thiết lập thời gian chờ tối đa (timeout) cho frame
cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)

while True:
    success, frame = cap.read()
    if not success: break

    qr_codes = decode(frame)

    # Nếu không thấy mã QR nào -> Reset trạng thái để nhận diện lại vật tiếp theo
    if len(qr_codes) == 0:
        last_qr_content = None 
    
    else:
        for code in qr_codes:
            content = code.data.decode('utf-8')

            # LUÔN VẼ KHUNG XANH ĐỂ GIÁM SÁT
            pts = np.array([code.polygon], np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (0, 255, 0), 3)
            cv2.putText(frame, content, (code.rect.left, code.rect.top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # CHỈ IN TERMINAL VÀ GỬI PLC KHI LÀ VẬT MỚI
            if content != last_qr_content:
                print(f"\n[PHÁT HIỆN] Nội dung mã: {content}")
                last_qr_content = content 

                # Phân loại
                if content == "mã hàng 1":
                    send_to_plc(1)
                elif content == "mã hàng 2":
                    send_to_plc(2)
                elif content == "mã hàng 3":
                    send_to_plc(3)
                elif content == "mã hàng 4":
                    send_to_plc(4)
                else:
                    send_to_plc(99) # Mã hàng lạ

    # Hiển thị cửa sổ Camera
    cv2.imshow('DO AN TOT NGHIEP - TIEN ANH', frame)

    # Nhấn 'q' để dừng (tần số quét 10Hz để tiết kiệm CPU)
    if cv2.waitKey(100) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
client.close()
print("\nĐã đóng kết nối và thoát chương trình.")