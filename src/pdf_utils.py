from pdf2image import convert_from_path
from io import BytesIO
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_pdf_file_name(user_id):
    return f"{user_id}.pdf"


def convert_pdf_to_images(file_name):
    return convert_from_path(file_name)


def get_pdf_page_image(images, page):
    img_byte_array = BytesIO()
    images[page - 1].save(img_byte_array, format='PNG')
    img_byte_array.seek(0)
    return img_byte_array


def build_pdf_nav_keyboard(current_page, total_pages, user_id):
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"pdf_prev_{current_page-1}_{total_pages}_{user_id}"))
    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"pdf_next_{current_page+1}_{total_pages}_{user_id}"))
    return InlineKeyboardMarkup([buttons])
