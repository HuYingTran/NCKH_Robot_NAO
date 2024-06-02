import cv2
import numpy as np

# Open the video file
# cap = cv2.VideoCapture("video/video_2.mp4")


# Check if the video opened successfully
# if not cap.isOpened():
#     print("Không thể mở video")
#     exit()

# Define the rectangle region of interest (ROI)
# Adjust these values to define the rectangle position and size
w, h = 600, 600

# Loop through each frame in the video
# while cap.isOpened():
while 1:
    # Read a frame
    # ret, frame = cap.read()

    # Check if the frame was read successfully
    if 1:
        frame = cv2.imread('anh1.png')
        y0, x0, channels = frame.shape

        x = int(x0/2-w/2)
        y = int(y0-h)

        # Define the region of interest (ROI)
        roi = frame[y:y+h, x:x+w]

        # Convert the ROI to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to the grayscale image
        blurred = cv2.GaussianBlur(gray, (1, 1), 100)

        # Tạo kernel (cấu trúc hình thái)
        kernel = np.ones((5,5), np.uint8)

        # Use Canny edge detection to detect edges
        edges = cv2.Canny(blurred, 10, 100)
        cv2.imshow("canny",edges)

        # Dãn ảnh
        dilated_image = cv2.dilate(edges, kernel, iterations=5)
        cv2.imshow("dan",dilated_image)

        # Thu nhỏ ảnh
        eroded_image = cv2.erode(dilated_image, kernel, iterations=5)
        cv2.imshow("thu",eroded_image)

        cv2.imshow("canny",eroded_image)

        # Apply Hough Line Transform to detect lines
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=10, minLineLength=1, maxLineGap=5)

        # Draw the detected lines on the ROI
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(roi, (x1, y1), (x2, y2), (0, 0, 255), 2)

        # Place the processed ROI back into the frame
        frame[y:y+h, x:x+w] = roi

        # Draw the ROI rectangle on the frame
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        # Display the result
        cv2.imshow('Stair Detection', frame)

        # Wait for 25ms and check if the user pressed 'q' to quit
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
    # else:
    #     break

# Release the video capture object and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()
