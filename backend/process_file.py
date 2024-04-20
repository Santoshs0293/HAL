from PIL import Image, ImageEnhance, ImageFilter
from pdf2image import convert_from_path
from transformers import MarianMTModel, MarianTokenizer
import pytesseract
from fpdf import FPDF
import subprocess
import os
from docx import Document
from concurrent.futures import ProcessPoolExecutor, as_completed
import sys
import fitz 

# Function to convert DOC to PDF using LibreOffice
def convert_doc_to_pdf(doc_path, pdf_path):
    subprocess.run(['libreoffice', '--convert-to', 'pdf', '--outdir', os.path.dirname(pdf_path), doc_path])

# Function to convert PDF to images
def convert_pdf_to_images(pdf_path):
    images = convert_from_path(pdf_path)
    return images

# Function to convert image to text
def extract_text_from_image(image):
    image = preprocess_image(image)
    text = pytesseract.image_to_string(image, lang='rus')
    return text

# Function to extract text from different file formats
def extract_text_from_file(file_path):
    text = ""
    file_path_lower = file_path.lower()  # Use a lower case version of file_path to simplify checks

    if file_path_lower.endswith(('.jpg', '.png', '.jpeg', '.gif', '.bmp', '.tiff', '.tif')):
        try:
            image = Image.open(file_path)
            text = extract_text_from_image(image)
        except Exception as e:
            text = "Failed to process image: " + str(e)
            print(text)  # More detailed error printout

    elif file_path_lower.endswith('.pdf'):
        try:
            images = convert_pdf_to_images(file_path)
            for img in images:
                img_text = extract_text_from_image(img)
                text += img_text + "\n"  # Add a newline between pages
        except Exception as e:
            text = "Failed to process PDF: " + str(e)
            print(text)  # More detailed error printout

    else:
        text = "Unsupported file format."

    return text

# Function to preprocess image for better OCR results
def preprocess_image(image):
    """Enhance image for better OCR results."""
    image = image.convert('L')  # Convert to grayscale
    image = image.filter(ImageFilter.MedianFilter(size=3))  # Apply a median filter
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)  # Increase contrast
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2)  # Increase sharpness
    return image

# Function to translate Russian text to English
import re

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

        # Remove consecutive duplicate characters, words, or groups of words
        cleaned_translation = re.sub(r'([^\W\d_])\1+', r'\1', translation)  # Remove consecutive duplicate characters excluding digits
        cleaned_translation = re.sub(r'\b(\w+)(?:\W+\1\b)+', r'\1', cleaned_translation,
                                    flags=re.IGNORECASE)  # Remove consecutive duplicate words
        cleaned_translation = re.sub(r'((?:\b\w+\b(?:\W+|$)){3,})\1+', r'\1', cleaned_translation,
                                    flags=re.IGNORECASE)  # Remove consecutive duplicate groups of words

        # Remove fully repeated phrases
        cleaned_translation = re.sub(r'\b(\w+(?:\s+\w+)+)\b(?=.*\b\1\b)', '', cleaned_translation,
                                     flags=re.IGNORECASE)
        
        # Remove consecutive duplicate phrases
        cleaned_translation = re.sub(r'(\b(?:\w+(?:\s+|$)){3,})\1+', r'\1', cleaned_translation, flags=re.IGNORECASE)

        # Remove repetitive sequences such as "♪" and spaces
        cleaned_translation = re.sub(r'(?:♪|\s)+', ' ', cleaned_translation)
        # Regex to remove consecutive duplicate symbols specified
        cleaned_translation = re.sub(r'([~`!@#$%^&*,.;:"?<>/\\\\\ ])\1+', r'\1', cleaned_translation)

        translated_paragraphs.append(cleaned_translation)

    final_translation = ". ".join(translated_paragraphs)
    return final_translation

# Function to handle different input types (image, PDF)
def handle_input(input_path):
    if os.path.isfile(input_path):
        return extract_text_from_file(input_path)
    else:
        raise ValueError("Input path does not exist or is not a file.")

# Function to create a DOCX file from translated text
def create_docx(translated_text, output_path):
    doc = Document()
    doc.add_paragraph(translated_text)
    doc.save(output_path)

# Function to create a PDF file from translated text
def create_pdf(translated_text, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, translated_text)
    pdf.output(output_path)

def clear_folder(folder_path):
    """Clears all files in the specified folder."""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            
# Function to process a single file
def process_file(input_path):
    try:
        ocr_text = handle_input(input_path)
        translated_text = translate_russian_to_english(ocr_text)
        output_folder = 'Download'
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        else:
            clear_folder(output_folder)  # Clear existing files in the folder

        output_file_name = f"output_{os.path.basename(input_path)}.docx"
        output_path = os.path.join(output_folder, output_file_name)
        create_docx(translated_text, output_path)
        print(f"File processed: {input_path}")
        print(f"Output DOCX: {output_path}")
    except Exception as e:
        print(f"Error processing file {input_path}: {e}")

# Function to process multiple files in parallel
def process_files(input_paths):
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_file, path) for path in input_paths]
        for future in as_completed(futures):
            if future.exception() is not None:
                print(f"Error processing file: {future.exception()}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_paths = sys.argv[1:]
        process_files(input_paths)
    else:
        print("No input files provided.")
