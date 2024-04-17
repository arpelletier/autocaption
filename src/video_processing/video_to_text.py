import os

from PIL import Image
import pytesseract

from ..logger import setup_logger

# Initialize logger
logger = setup_logger()


def extract_image_text(input_dir):
    """ Extracts text from all .jpg images in the specified directory. """
    text_dict = {}
    for filename in os.listdir(input_dir):
        if filename.endswith('.jpg'):
            image_path = os.path.join(input_dir, filename)
            image = Image.open(image_path)
            extracted_text = pytesseract.image_to_string(image)
            text_dict[filename] = extracted_text.strip()
    # TODO: Resulting text is very dirty and needs data cleaning.
    return text_dict


def extract_image_description(input_dir):
    ''' This function generates a description of the .jpg image '''
    # TODO complete implementation
    print("This function is not implemented yet.")
    return None