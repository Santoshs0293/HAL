import cv2
import easyocr
import matplotlib.pyplot as plt
from transformers import MarianMTModel, MarianTokenizer
from pdf2image import convert_from_path
import numpy as np
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import sys

# Function to translate Russian text to English
def translate_russian_to_english(long_text, max_length=512):
    model_name = "Helsinki-NLP/opus-mt-ru-en"
    model = MarianMTModel.from_pretrained(model_name)
    tokenizer = MarianTokenizer.from_pretrained(model_name)

    paragraphs = [paragraph.strip() for paragraph in long_text.split('.') if paragraph.strip()]
    translated_paragraphs = []
    for paragraph in paragraphs:
        inputs = tokenizer(paragraph, return_tensors="pt", truncation=True)
        translation_ids = model.generate(**inputs, max_length=max_length)
        translation = tokenizer.decode(translation_ids[0], skip_special_tokens=True)
        translated_paragraphs.append(translation)

    final_translation = ". ".join(translated_paragraphs)
    return final_translation

def clear_folder(folder_path):
    """Clears all files in the specified folder."""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

# Function to process image or PDF
def process_file(file_path):
    print("File Path:", file_path)
    print("Lowercased File Path:", file_path.lower())
    if file_path.lower().endswith(('.jpg', '.png', '.jpeg', '.gif', '.bmp', '.tiff', '.raw', '.tif')):
        img = cv2.imread(file_path)
    elif file_path.lower().endswith('.pdf'):
        images = convert_from_path(file_path)
        # For simplicity, consider only the first page of the PDF
        img = cv2.cvtColor(np.array(images[0]), cv2.COLOR_RGB2BGR)
    else:
        print("Unsupported file format.")
        return
    # Get the base name of the input file
    base_name = os.path.basename(file_path)
    # Remove extension from the base name
    base_name = os.path.splitext(base_name)[0]

    # Initialize text detector
    reader = easyocr.Reader(['ru'], gpu=False)

    # Detect text on image
    results = reader.readtext(img)

    # Print detected text
    for result in results:
        print("Detected Text:", result[1], "Confidence:", result[2])

    # Translate detected text
    translated_texts = [translate_russian_to_english(result[1]) for result in results]

    # Draw bounding box and translated text
    for (bbox, _, _), translated_text in zip(results, translated_texts):
        # Format bounding box
        bbox = [(int(point[0]), int(point[1])) for point in bbox]
        # Draw filled rectangle (white color)
        cv2.rectangle(img, bbox[0], bbox[2], (255, 255, 255), -1)  # -1 for filled rectangle
        # Draw rectangle outline (green color)
        cv2.rectangle(img, bbox[0], bbox[2], (0, 255, 0), 2)
        # Get text size
        text_size = cv2.getTextSize(translated_text, cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, 2)[0]
        # Calculate text position
        text_x = bbox[0][0] + (bbox[2][0] - bbox[0][0] - text_size[0]) // 2
        text_y = bbox[0][1] + (bbox[2][1] - bbox[0][1] + text_size[1]) // 2
        # Draw translated text
        cv2.putText(img, translated_text, (text_x, text_y), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1.2, (255, 0, 0), 2)
    
    output_folder = 'Download'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    else:
        clear_folder(output_folder)  # Clear existing files in the folder

    
    # Save the image with bounding boxes and translated text
    
    output_file = os.path.join(output_folder, f"{base_name}_translated.jpg")
    cv2.imwrite(output_file, img)

    # Display the image with bounding boxes and translated text
    plt.figure(figsize=(10, 10))
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.axis('off')
    #plt.show()

# Example usage
# file_path = '/home/cdot/Desktop/translator_app/backend/uploads/test1.pdf'
# process_file(file_path)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        process_file(file_path)
    else:
        print("No input files provided.")