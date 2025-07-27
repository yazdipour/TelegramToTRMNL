"""
EPUB to PDF conversion utilities for TRMNL Telegram Bot

This module provides EPUB to PDF conversion using Pandoc:
1. Pandoc (EPUB → HTML with embedded images)
2. ReportLab (HTML → PDF with cover image support)
3. Error handling with installation instructions

The conversion process: EPUB → HTML (with images) → PDF with ReportLab
"""

import os
import subprocess
import logging
import shutil
import re
import base64
import io

logger = logging.getLogger(__name__)

# Default dimensions in pixels for TRMNL device
DEFAULT_WIDTH = 480
DEFAULT_HEIGHT = 800

def get_dimensions():
    """Get page dimensions in points (ReportLab units)"""
    width = int(os.getenv('TRMNL_WIDTH', DEFAULT_WIDTH))
    height = int(os.getenv('TRMNL_HEIGHT', DEFAULT_HEIGHT))
    # Convert pixels to points accurately (assuming 96 DPI)
    width_points = width * 72.0 / 96.0
    height_points = height * 72.0 / 96.0
    logger.info(f"Page dimensions: {width_points:.1f} x {height_points:.1f} points")
    return width_points, height_points

def _convert_with_pandoc(epub_path, pdf_path):
    """Convert EPUB to PDF using Pandoc → HTML → ReportLab"""
    if not shutil.which("pandoc"):
        raise FileNotFoundError("Pandoc not found")
    
    logger.info("Converting EPUB with Pandoc")
    html_file = f"{pdf_path}.html"
    
    try:
        # Try to convert with embedded images first
        cmd = [
            "pandoc", epub_path, "-o", html_file,
            "--standalone", "--self-contained", 
            "--extract-media=.", "--embed-resources"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.warning("EPUB→HTML with images failed, trying basic conversion")
            # Fallback to basic conversion
            cmd = ["pandoc", epub_path, "-o", html_file, "--standalone", "--self-contained"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise RuntimeError(f"Pandoc failed: {result.stderr}")
        
        # Convert HTML to PDF
        _convert_html_to_pdf(html_file, pdf_path)
        
    finally:
        # Cleanup
        if os.path.exists(html_file):
            os.remove(html_file)

def _convert_html_to_pdf(html_file, pdf_path):
    """Convert HTML to PDF using ReportLab with cover image support"""
    try:
        from reportlab.pdfgen import canvas
        from bs4 import BeautifulSoup
        from reportlab.lib.utils import ImageReader
        from PIL import Image
        
        # Read and parse HTML
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        width, height = get_dimensions()
        c = canvas.Canvas(pdf_path, pagesize=(width, height))
        
        # Style constants
        font_name, font_size, line_height, margin = "Helvetica", 10, 14, 30
        y_position = height - margin
        content_added = False
        
        # Process cover image first
        cover_added = _add_cover_image(c, soup, width, height, margin, font_size, line_height)
        if cover_added:
            content_added = True
            c.showPage()
            y_position = height - margin
        
        # Process text content  
        text_added = _add_text_content(c, soup, width, height, margin, font_name, font_size, line_height, y_position)
        if text_added:
            content_added = True
        
        # Fallback message if no content
        if not content_added:
            c.setFont(font_name, font_size)
            c.drawString(margin, height - margin, "No content could be extracted from this EPUB file.")
        
        c.save()
        logger.info(f"Successfully converted HTML to PDF: {pdf_path}")
        
    except ImportError as e:
        logger.warning(f"Missing library for image processing: {e}")
        _convert_html_to_pdf_text_only(html_file, pdf_path)
    except Exception as e:
        logger.error(f"HTML to PDF conversion failed: {e}")
        raise

def _add_cover_image(canvas_obj, soup, width, height, margin, font_size, line_height):
    """Add cover image to PDF if found in HTML"""
    try:
        from PIL import Image
        from reportlab.lib.utils import ImageReader
        
        img_tags = soup.find_all('img')
        if not img_tags:
            return False
        
        for img in img_tags:
            img_src = img.get('src', '')
            img_alt = img.get('alt', '').lower()
            
            # Check if this looks like a cover
            if ('cover' in img_src.lower() or 'cover' in img_alt or img == img_tags[0]):
                if img_src.startswith('data:image'):
                    try:
                        # Process base64 image
                        header, data = img_src.split(',', 1)
                        image_data = base64.b64decode(data)
                        pil_image = Image.open(io.BytesIO(image_data))
                        
                        # Calculate scaling
                        img_width, img_height = pil_image.size
                        max_width = width - 2 * margin
                        max_height = (height - 2 * margin) * 0.6
                        scale = min(max_width / img_width, max_height / img_height)
                        new_width, new_height = img_width * scale, img_height * scale
                        
                        # Center and draw image
                        x_img = (width - new_width) / 2
                        y_img = height - margin - new_height
                        
                        canvas_obj.drawImage(ImageReader(pil_image), x_img, y_img, 
                                           width=new_width, height=new_height)
                        
                        # Add label
                        canvas_obj.setFont("Helvetica-Bold", font_size + 2)
                        canvas_obj.drawString(margin, height - margin, "COVER")
                        
                        logger.info("Added cover image to PDF")
                        return True
                        
                    except Exception as e:
                        logger.warning(f"Failed to process cover image: {e}")
        
        return False
    except ImportError:
        logger.warning("PIL not available for image processing")
        return False
    except Exception as e:
        logger.warning(f"Error processing cover: {e}")
        return False

def _add_text_content(canvas_obj, soup, width, height, margin, font_name, font_size, line_height, y_position):
    """Add text content to PDF"""
    try:
        # Remove images and scripts for text extraction
        for element in soup(["script", "style", "img"]):
            element.decompose()
        
        # Extract and clean text
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        text = '\n'.join(line for line in lines if line)
        
        if not text.strip():
            return False
        
        # Process paragraphs
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Word wrapping
            words = paragraph.split()
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                text_width = canvas_obj.stringWidth(test_line, font_name, font_size)
                
                if text_width > (width - 2 * margin) and current_line:
                    # Draw current line and start new line
                    if y_position < margin:
                        canvas_obj.showPage()
                        y_position = height - margin
                    
                    canvas_obj.setFont(font_name, font_size)
                    canvas_obj.drawString(margin, y_position, ' '.join(current_line))
                    y_position -= line_height
                    current_line = [word]
                else:
                    current_line.append(word)
            
            # Draw remaining text
            if current_line:
                if y_position < margin:
                    canvas_obj.showPage()
                    y_position = height - margin
                
                canvas_obj.setFont(font_name, font_size)
                canvas_obj.drawString(margin, y_position, ' '.join(current_line))
                y_position -= line_height
            
            # Paragraph spacing
            y_position -= line_height * 0.5
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding text content: {e}")
        return False

def _convert_html_to_pdf_text_only(html_file, pdf_path):
    """Fallback: Convert HTML to PDF with text only (no images)"""
    try:
        from reportlab.pdfgen import canvas
        from bs4 import BeautifulSoup
        
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        text = '\n'.join(line for line in lines if line)
        
        width, height = get_dimensions()
        c = canvas.Canvas(pdf_path, pagesize=(width, height))
        
        # Simple text rendering
        font_name, font_size, line_height, margin = "Helvetica", 10, 14, 30
        y_position, x_position = height - margin, margin
        
        for paragraph in text.split('\n\n'):
            if not paragraph.strip():
                continue
            
            words = paragraph.split()
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                text_width = c.stringWidth(test_line, font_name, font_size)
                
                if text_width > (width - 2 * margin) and current_line:
                    if y_position < margin:
                        c.showPage()
                        y_position = height - margin
                    
                    c.setFont(font_name, font_size)
                    c.drawString(x_position, y_position, ' '.join(current_line))
                    y_position -= line_height
                    current_line = [word]
                else:
                    current_line.append(word)
            
            if current_line:
                if y_position < margin:
                    c.showPage()
                    y_position = height - margin
                
                c.setFont(font_name, font_size)
                c.drawString(x_position, y_position, ' '.join(current_line))
                y_position -= line_height
            
            y_position -= line_height * 0.5
        
        c.save()
        logger.info(f"Successfully converted HTML to PDF (text only): {pdf_path}")
        
    except Exception as e:
        logger.error(f"Text-only conversion failed: {e}")
        _create_simple_text_pdf(html_file, pdf_path)

def _create_simple_text_pdf(html_file, pdf_path):
    """Create a minimal PDF from HTML file as last resort"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', content)
        text = re.sub(r'\s+', ' ', text).strip()
        
        width, height = get_dimensions()
        
        # Create minimal PDF
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4\n')
            f.write(f'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'.encode())
            f.write(f'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'.encode())
            f.write(f'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 {width} {height}]/Contents 4 0 R>>endobj\n'.encode())
            
            text_content = f'BT /F1 12 Tf 50 {height-50} Td ({text[:500]}...) Tj ET'
            f.write(f'4 0 obj<</Length {len(text_content)}>>stream\n{text_content}\nendstream\nendobj\n'.encode())
            f.write(b'xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000200 00000 n \n')
            f.write(b'trailer<</Size 5/Root 1 0 R>>\nstartxref\n300\n%%EOF\n')
        
        logger.info(f"Created simple text PDF: {pdf_path}")
        
    except Exception as e:
        logger.error(f"Simple PDF creation failed: {e}")
        _create_error_pdf(pdf_path, f"Text extraction failed: {str(e)}")

def _create_error_pdf(pdf_path, error_message):
    """Create an error PDF with installation instructions"""
    try:
        from reportlab.pdfgen import canvas
        
        width, height = get_dimensions()
        c = canvas.Canvas(pdf_path, pagesize=(width, height))
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(30, height - 50, "EPUB Conversion Error")
        
        c.setFont("Helvetica", 10)
        y_pos = height - 80
        
        lines = [
            error_message, "",
            "To convert EPUB files, install Pandoc:", "",
            "1. Pandoc (Required):",
            "   Download: https://pandoc.org/",
            "   After installation, restart the bot.", "",
            "The bot will automatically detect Pandoc."
        ]
        
        for line in lines:
            if y_pos < 30:
                break
            c.drawString(30, y_pos, line)
            y_pos -= 15
        
        c.save()
        logger.info(f"Created error PDF: {pdf_path}")
        
    except ImportError:
        # Fallback to text file
        with open(pdf_path.replace('.pdf', '_error.txt'), 'w') as f:
            f.write(f"EPUB Conversion Error: {error_message}\n")
            f.write("Please install Pandoc from https://pandoc.org/\n")
        logger.warning("Created error text file instead of PDF")

# Debug function for troubleshooting
def debug_epub_content(epub_path):
    """Analyze EPUB content (requires ebooklib)"""
    try:
        import ebooklib
        from ebooklib import epub
        
        book = epub.read_epub(epub_path)
        
        print(f"EPUB Analysis for: {epub_path}")
        print("=" * 50)
        
        all_items = list(book.get_items())
        doc_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        image_items = list(book.get_items_of_type(ebooklib.ITEM_IMAGE))
        
        print(f"Total items: {len(all_items)}")
        print(f"Document items: {len(doc_items)}")
        print(f"Image items: {len(image_items)}")
        print("\nDocument files:")
        for i, item in enumerate(doc_items):
            print(f"{i+1}. {item.file_name}")
        
        print("\nRecommendation: Use Calibre's ebook-convert for best results")
        
    except ImportError:
        print("ebooklib not available for debugging")
        print("Install with: pip install ebooklib")
    except Exception as e:
        print(f"Error analyzing EPUB: {e}")

def convert_epub_to_pdf(epub_path, pdf_path):
    """
    Convert EPUB to PDF using Pandoc only
    
    Process:
    1. Pandoc (EPUB → HTML with embedded images)
    2. ReportLab (HTML → PDF with cover image support)
    3. Error PDF if Pandoc fails
    """
    try:
        logger.info(f"Converting EPUB {epub_path} to PDF {pdf_path}")
        
        # Use Pandoc only
        _convert_with_pandoc(epub_path, pdf_path)
        logger.info(f"Successfully converted EPUB to PDF: {pdf_path}")
        
    except FileNotFoundError:
        error_msg = "Pandoc not found. Please install Pandoc from https://pandoc.org/"
        logger.error(error_msg)
        _create_error_pdf(pdf_path, error_msg)
        
    except Exception as e:
        error_msg = f"EPUB conversion failed: {str(e)}"
        logger.error(error_msg)
        _create_error_pdf(pdf_path, error_msg)
