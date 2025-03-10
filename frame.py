import os
import cv2
from glob import glob

def create_dir(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except OSError:
        print(f"ERROR creating directory with name {path}")

def blend_edges(inpainted_frame, mask):
    # Find contours of the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blended_frame = inpainted_frame.copy()
    
    for contour in contours:
        # Create a bounding box around each contour
        x, y, w, h = cv2.boundingRect(contour)
        roi = inpainted_frame[y:y+h, x:x+w]
        
        # Apply Gaussian blur to the edges of the ROI
        blurred_roi = cv2.GaussianBlur(roi, (21, 21), 0)
        blended_frame[y:y+h, x:x+w] = blurred_roi
    
    return blended_frame

def extract_and_save_frames(video_path, save_dir):
    name = os.path.splitext(os.path.basename(video_path))[0]
    frames_path = os.path.join(save_dir, "frames", name)
    processed_path = os.path.join(save_dir, "processed", name)
    
    create_dir(frames_path)
    create_dir(processed_path)
    
    cap = cv2.VideoCapture(video_path)
    idx = 0
    fgbg = cv2.createBackgroundSubtractorMOG2(history=700, varThreshold=25, detectShadows=False)
    prev_frame = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Save the extracted frame
        cv2.imwrite(f"{frames_path}/{idx}.png", frame)
        
        # Convert frame to grayscale for difference calculation
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_frame is not None:
            # Compute the absolute difference between consecutive frames
            diff_frame = cv2.absdiff(prev_frame, gray_frame)
            
            # Threshold the difference to get the moving objects
            _, diff_frame = cv2.threshold(diff_frame, 25, 255, cv2.THRESH_BINARY)
            
            # Apply Gaussian blur to smooth the difference frame
            diff_frame = cv2.GaussianBlur(diff_frame, (5, 5), 0)
            
            # Refine the mask using morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            diff_frame = cv2.morphologyEx(diff_frame, cv2.MORPH_OPEN, kernel, iterations=2)
            diff_frame = cv2.morphologyEx(diff_frame, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            # Apply background subtraction
            fgmask = fgbg.apply(frame)
            
            # Perform additional morphological operations to clean up the foreground mask
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel, iterations=3)
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, kernel, iterations=3)
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_ERODE, kernel, iterations=2)
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_DILATE, kernel, iterations=2)
            
            # Combine the difference frame with the foreground mask
            combined_mask = cv2.bitwise_or(fgmask, diff_frame)
            
            # Refine the combined mask
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=3)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
            
            # Inpaint the combined mask area in the frame
            inpainted_frame = cv2.inpaint(frame, combined_mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
            
            # Blend the edges of the inpainted area to improve quality
            blended_frame = blend_edges(inpainted_frame, combined_mask)
            
            # Save the processed frame
            cv2.imwrite(f"{processed_path}/{idx}.png", blended_frame)
        
        prev_frame = gray_frame.copy()
        idx += 1
    
    cap.release()

if __name__ == "__main__":
    video_paths = glob("all_videos/*")
    save_dir = "save"
    
    for path in video_paths:
        extract_and_save_frames(path, save_dir)
