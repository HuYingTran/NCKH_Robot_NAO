import cv2
import numpy as np

# Đọc ảnh từ file
image = cv2.imread('anhCauThang.jpg')

# Chuyển đổi ảnh sang màu xám
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Áp dụng bộ lọc Gaussian để làm mờ ảnh
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
cv2.imshow('mo',blurred)

# Sử dụng bộ lọc Canny để phát hiện các cạnh
edges = cv2.Canny(blurred, 10, 80)
cv2.imshow('canh',edges)

# Áp dụng Hough Line Transform để phát hiện các đường thẳng
lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=10, minLineLength=1, maxLineGap=5)

# Vẽ các đường thẳng lên ảnh gốc
if lines is not None:
    for line in lines:
        x1, y1, x2, y2 = line[0]
        cv2.line(image, (x1, y1), (x2, y2), (0, 0, 255), 5)

# Hiển thị ảnh kết quả
cv2.imshow('Stair Detection', image)
cv2.waitKey(0)
cv2.destroyAllWindows()
