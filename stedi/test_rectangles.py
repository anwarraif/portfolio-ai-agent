import cv2
import numpy as np

# Load image
img = cv2.imread('sample_test.jpeg')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Find contours
contours, _ = cv2.findContours(cv2.Canny(gray, 50, 150), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Detect rectangles and mark centers and corners
for contour in contours:
    approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
    if len(approx) == 4:  # Rectangle has 4 vertices
        # Mark center
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            cv2.circle(img, (cx, cy), 5, (0, 0, 255), -1)
        
        # Mark corners
        for point in approx:
            cv2.circle(img, tuple(point[0]), 3, (0, 0, 255), -1)

cv2.imwrite('output.jpg', img)
