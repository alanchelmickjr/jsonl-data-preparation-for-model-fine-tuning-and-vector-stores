import os
import json
from openai import OpenAI
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# OpenAI API key (replace with your actual API key)
client = OpenAI(
    api_key='YOUR-OPENAI-API-KEY')

# Path to Tesseract executable (only needed for Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Paths
pdf_path = 'calc.pdf'
output_image_dir = 'output_images'
output_text_file = 'extracted_text.txt'
output_jsonl_file = 'segmented_text.jsonl'

# Ensure output directory exists
os.makedirs(output_image_dir, exist_ok=True)


def convert_pdf_to_images(pdf_path, output_image_dir):
    # Convert PDF to images
    images = convert_from_path(pdf_path)
    image_paths = []
    print("Converting PDF to images", end="")
    for i, image in enumerate(images):
        image_path = os.path.join(output_image_dir, f'page_{i + 1}.png')
        image.save(image_path, 'PNG')
        image_paths.append(image_path)
        print(".", end="", flush=True)
    print(" Done!")
    return image_paths


def extract_text_from_images(image_paths):
    all_text = ""
    print("Extracting text from images", end="")
    for i, image_path in enumerate(image_paths):
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        all_text += f'Text from page {i + 1}:\n{text}\n' + '-' * 80 + '\n'
        print(".", end="", flush=True)
    print(" Done!")
    return all_text


def analyze_and_format_text(text):
    # Split the text into smaller chunks
    max_chunk_size = 4096  # Adjust this size based on your needs and model limits
    text_chunks = [text[i:i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]

    formatted_text = ""
    print("Analyzing and formatting text", end="")
    for chunk in text_chunks:
        prompt = f"Analyze the following text and provide it sectioned by chapters, verses, sections, topics, and overall context where possible. Return the text formatted:\n\n{chunk}\n\nFormatted Text:"

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                n=1,
                stop=None,
                temperature=0.7
            )

            message_content = response.choices[0].message['content']
            formatted_text += message_content.strip() + "\n\n"
            print(".", end="", flush=True)

        except Exception as e:
            print(f"\nAn error occurred: {e}")
            continue

    print(" Done!")
    return formatted_text.strip()


def segment_text_by_analysis(formatted_text):
    # This function can be customized based on the formatted text returned by GPT # For now, we assume the formatted text is already sectioned appropriately
    sections = formatted_text.split('\n\n')
    segmented_text = []
    print("Segmenting text by analysis", end="")
    for section in sections:
        title, content = section.split('\n', 1)
        segmented_text.append((title.strip(), content.strip()))
        print(".", end="", flush=True)
    print(" Done!")
    return segmented_text


def prepare_jsonl_data(segmented_text):
    jsonl_data = []
    print("Preparing JSONL data", end="")
    for section_title, section_content in segmented_text:
        # Example metadata extraction (customize as needed)
        metadata = {
            "section_title": section_title,
            "length": len(section_content.split())
        }
        jsonl_entry = {
            "text": section_content,
            "metadata": metadata
        }
        jsonl_data.append(jsonl_entry)
        print(".", end="", flush=True)
    print(" Done!")
    return jsonl_data


def save_text_to_file(text, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)


def save_jsonl_to_file(jsonl_data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        for entry in jsonl_data:
            f.write(json.dumps(entry) + '\n')


def main():
    if not os.path.exists(output_image_dir) or not os.listdir(output_image_dir):
        convert_images = input("Do you want to convert the PDF to images? (yes/no): ").strip().lower()
        if convert_images == 'yes':
            print("Converting PDF to images...")
            image_paths = convert_pdf_to_images(pdf_path, output_image_dir)
            print(f"Converted {len(image_paths)} pages to images.")
        else:
            print("Skipping PDF to images conversion.")
            image_paths = [os.path.join(output_image_dir, f) for f in os.listdir(output_image_dir)]
    else:
        print("Images already exist. Skipping PDF to images conversion.")
        image_paths = [os.path.join(output_image_dir, f) for f in os.listdir(output_image_dir)]

    if not os.path.exists(output_text_file):
        extract_text = input("Do you want to extract text from images? (yes/no): ").strip().lower()
        if extract_text == 'yes':
            print("Extracting text from images...")
            extracted_text = extract_text_from_images(image_paths)
            save_text_to_file(extracted_text, output_text_file)
            print(f"Text extraction complete. Check '{output_text_file}' for results.")
        else:
            print("Skipping text extraction.")
            with open(output_text_file, 'r', encoding='utf-8') as f:
                extracted_text = f.read()
    else:
        print("Text file already exists. Skipping text extraction.")
        with open(output_text_file, 'r', encoding='utf-8') as f:
            extracted_text = f.read()

    if not os.path.exists(output_text_file.replace('.txt', '_formatted.txt')):
        analyze_text = input("Do you want to analyze and format the text? (yes/no): ").strip().lower()
        if analyze_text == 'yes':
            print("Analyzing and formatting text...")
            formatted_text = analyze_and_format_text(extracted_text)
            save_text_to_file(formatted_text, output_text_file.replace('.txt', '_formatted.txt'))
            print(
                f"Text analysis and formatting complete. Check '{output_text_file.replace('.txt', '_formatted.txt')}' for results.")
        else:
            print("Skipping text analysis and formatting.")
            with open(output_text_file.replace('.txt', '_formatted.txt'), 'r', encoding='utf-8') as f:
                formatted_text = f.read()
    else:
        print("Formatted text file already exists. Skipping text analysis and formatting.")
        with open(output_text_file.replace('.txt', '_formatted.txt'), 'r', encoding='utf-8') as f:
            formatted_text = f.read()

    if not os.path.exists(output_jsonl_file):
        segment_text = input("Do you want to segment the text by analysis? (yes/no): ").strip().lower()
        if segment_text == 'yes':
            print("Segmenting text by analysis...")
            segmented_text = segment_text_by_analysis(formatted_text)

            print("Preparing JSONL data...")
            jsonl_data = prepare_jsonl_data(segmented_text)
            save_jsonl_to_file(jsonl_data, output_jsonl_file)
            print(f"JSONL conversion complete. Check '{output_jsonl_file}' for results.")
        else:
            print("Skipping text segmentation and JSONL conversion.")
    else:
        print("JSONL file already exists. Skipping text segmentation and JSONL conversion.")


if __name__ == "__main__":
    main()
