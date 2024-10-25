import os
import tempfile
from io import BytesIO
from django.shortcuts import render, redirect
from django.core.files import File
from PIL import Image
import fitz
from chatbookapp.models import Book
from .insert_pdf_vectore import PDFProcessor
processor = PDFProcessor()

def process_pdf(pdf_path, filename):
    doc = fitz.open(pdf_path)
    
    if len(doc) > 0:
        page = doc.load_page(0)  # Load the first page
        pix = page.get_pixmap()  # Render page to an image
        
        # Convert pixmap to image
        img_data = pix.tobytes('png')
        img = Image.open(BytesIO(img_data))

        # Save image to a BytesIO object
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)

        # Create Book instance
        book = Book()
        book.book_name = os.path.splitext(filename)[0]
        print("@@@@@@@ this is book name",book.book_name)
        # Save image and pdf
        book.image.save(f"{os.path.splitext(filename)[0]}.png", File(img_io), save=False)
        book.pdf.save(filename, File(open(pdf_path, 'rb')), save=False)
        
        # Save the book instance to the database
        book.save()
        processor.process_pdf(pdf_path,book.book_name)
        print(f"Processed and saved: {filename}")

    doc.close()

def handle_uploaded_file(file):
    # Create a temporary file to store the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        for chunk in file.chunks():
            temp_file.write(chunk)
    return temp_file.name
