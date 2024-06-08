# -*- coding: utf-8 -*-
import cv2
import numpy as np

center_x, center_y = 640/2 ,400
w, h = 500, 400

def is_line_similar(line1, line2, threshold=10, distance_threshold = 10):
    """Kiểm tra xem hai đường thẳng có tương tự nhau không."""
    x1, y1, x2, y2 = line1[0]
    x3, y3, x4, y4 = line2[0]

    # Tính độ dốc của hai đường thẳng
    slope1 = (y2 - y1) / (x2 - x1) if (x2 - x1) != 0 else float('inf')
    slope2 = (y4 - y3) / (x4 - x3) if (x4 - x3) != 0 else float('inf')
    
    # Kiểm tra nếu độ dốc của hai đường thẳng gần bằng nhau
    if abs(slope1 - slope2) > threshold:
        return False
    
    # Tính khoảng cách từ các điểm của đường thẳng này tới đường thẳng kia
    def point_line_distance(px, py, x1, y1, x2, y2):
        """Tính khoảng cách từ điểm (px, py) tới đường thẳng qua (x1, y1) và (x2, y2)."""
        return abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1) / np.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)
    
    distance1 = point_line_distance(x3, y3, x1, y1, x2, y2)
    distance2 = point_line_distance(x4, y4, x1, y1, x2, y2)
    
    # Kiểm tra nếu khoảng cách từ các điểm này đều nhỏ hơn ngưỡng
    return distance1 < distance_threshold and distance2 < distance_threshold

def detect_canh(anh):
    frame = anh
    y0, x0, channels = frame.shape

    x = int(x0/2-w/2)
    y = int(y0-h-20)

    # Define the region of interest (ROI)
    roi = frame[y:y+h, x:x+w]

    # Convert the ROI to grayscale
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to the grayscale image
    blurred = cv2.GaussianBlur(gray, (9, 9), 10)
    cv2.imshow("blurred",blurred)

    # Tạo kernel (cấu trúc hình thái)
    kernel = np.ones((5,5), np.uint8)

    ng = 10
    # Use Canny edge detection to detect edges
    edges = cv2.Canny(blurred, ng,ng+5 )
    cv2.imshow("canny",edges)

    # Dãn ảnh
    dilated_image = cv2.dilate(edges, kernel, iterations=5)
    cv2.imshow("dilated_image",dilated_image)

    # Thu nhỏ ảnh
    eroded_image = cv2.erode(dilated_image, kernel, iterations=5)
    cv2.imshow("eroded_image",eroded_image)

    # cv2.imshow("canny",eroded_image)

    # Apply Hough Line Transform to detect lines
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=10, minLineLength=10, maxLineGap=100)

    # Loại bỏ các đường trùng lặp
    unique_lines = []
    mid_x, mid_y, angle = 0, 0, 0
    if lines is not None:
        for line in lines:
            is_duplicate = False
            for unique_line in unique_lines:
                if is_line_similar(line, unique_line):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_lines.append(line)
        
        unique_lines = unique_lines[::-1]
        x1m, y1m, x2m, y2m = unique_lines[0][0]
        min_line = unique_lines[0][0]

        for line in unique_lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(roi, (x1, y1), (x2, y2), (255, 0, 255), 5)
            if(x1m>x1):
                min_line = line

            # Vẽ các đường thẳng không trùng lặp lên ảnh gốc
        x1, y1, x2, y2 = min_line[0]
        cv2.line(roi, (x1, y1), (x2, y2), (0, 0, 255), 5)

        angle = np.arctan2(y2 - y1, x2 - x1)
        cv2.putText(roi, "{:.2f}".format(angle * 180 / np.pi), (x1+10, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 1, cv2.LINE_AA)

        mid_x, mid_y = (x1+x2)/2, (y1+y2)/2
        roi = cv2.circle(roi, (mid_x, mid_y), 10, (0, 0, 255), -1)
    # Place the processed ROI back into the frame
    roi = cv2.circle(roi, (center_x, center_y), 10, (0, 255, 0), -1)
    frame[y:y+h, x:x+w] = roi

    # Draw the ROI rectangle on the frame
    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)


    # Display the result
    return frame, mid_x, mid_y, angle


image = cv2.imread("anhCauThang.jpg")
image,x,y,e = detect_canh(image)
cv2.imshow("detect",image)

cv2.waitKey(0)

# Đóng tất cả các cửa sổ hiển thị
cv2.destroyAllWindows()