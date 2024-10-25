from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain.embeddings.openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
import PyPDF2
import fitz  # PyMuPDF
import uuid
from openai import OpenAI
import re
import pickle
import psycopg2
import numpy as np
import json
from PIL import Image
import ast
import pytesseract
import io
from pdf2image import convert_from_path
from django.conf import settings

class PDFProcessor:

    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

        # Initialize OpenAI Embeddings
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.OPENAI_API_KEY)

        # Database connection
        # self.connection = "postgresql+psycopg2://linuxbean:linux123@127.0.0.1:5432/harry"
        # self.sqlalchemy_connection = "postgresql+psycopg2://linuxbean:linux123@127.0.0.1:5432/harry"
        # self.psycopg2_connection = "dbname=harry user=linuxbean password=linux123 host=127.0.0.1 port=5432"
        self.connection = settings.CONNECTION_STRING
        self.sqlalchemy_connection = settings.CONNECTION_STRING
        self.psycopg2_connection = settings.PSYCOPG2_CONNECTION_STRING
        # Initialize PGVector
        self.collection_name = "exclusive_book"
        self.vectorstore = PGVector(
            embeddings=self.embeddings,
            collection_name=self.collection_name,
            connection=self.connection,
            use_jsonb=True,
        )

        with open('svm_model_embeddings.pkl', 'rb') as f:
            self.svm_model = pickle.load(f)

        # Set up OpenAI API key
        self.client = OpenAI(api_key=self.OPENAI_API_KEY)
        self.metadata_dict={}
        
        
    # def read_pdf(self, file_path, num_pages=5):
    #     """
    #     This function converts a PDF into images and extracts text from the first num_pages using pytesseract.
    #     """
    #     text = ""
    #     # Convert PDF to images
    #     images = convert_from_path(file_path)
        
    #     # Limit the extraction to the specified number of pages
    #     for i, image in enumerate(images[:num_pages]):
    #         # Perform OCR on each image
    #         text += pytesseract.image_to_string(image)
            
    #     return text
    
    def read_pdf(self, file_path, num_pages=10):
        # Read content from PDF file
        content = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in range(min(num_pages, len(pdf_reader.pages))):
                content += pdf_reader.pages[page].extract_text()
        return content

    def create_meaningful_chunks(self, content):
        # Create meaningful chunks using OpenAI API
        prompt = """You are a helpful assistant that creates meaningful chunks from text and provides the metadata like this:
        Summary:
        ..........
        Metadata:
        Title: [Insert Title]
        Author: [Insert Author]
        Publication Year: [Insert Year]
        Publisher: [Insert Publisher]
        Subject: [Insert Subject]
        .............
        ("The summary must begin with the keyword 'Summary', and the metadata must begin with the keyword 'Metadata'.")
        Note: Summary will be 150 - 250 words
        """
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Please create a meaningful summary from the following text:\n\n{content}"}
            ]
        )
        return response.choices[0].message.content

    def split_content(self, content):
        # Split content into summary and metadata
        summary_pattern = re.compile(r'Summary:(.*?)Metadata:', re.DOTALL)
        metadata_pattern = re.compile(r'Metadata:(.*)', re.DOTALL)

        summary_match = summary_pattern.search(content)
        metadata_match = metadata_pattern.search(content)

        if summary_match and metadata_match:
            summary = summary_match.group(1).strip()
            metadata = metadata_match.group(1).strip()
            return summary, metadata
        else:
            return None, None

    def extract_metadata(self, metadata):
        # Extract metadata into a dictionary
        if metadata is None:
            print("Warning: Metadata is None")
            return {}
        self.metadata_dict = {"id": str(uuid.uuid4())}
        lines = metadata.split('\n')
        for line in lines:
            if ': ' in line:
                key, value = line.split(': ', 1)
                self.metadata_dict[key.strip()] = value.strip()
        return self.metadata_dict

    def remove_null_characters(self, text):
        # Remove null characters from text
        return text.replace('\x00', '')

    def extract_text_from_pdf(self, pdf_path, bookname):
        # Extract text from PDF and create documents with metadata
        doc = fitz.open(pdf_path)
        text_with_metadata = []
        self.metadata_dict = {}

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = self.remove_null_characters(page.get_text())
            self.metadata_dict.update({"page": page_num + 1})
            self.metadata_dict.update({"filename": bookname})

            text_with_metadata.append(Document(
                page_content=text,
                metadata=self.metadata_dict.copy()
            ))
        self.metadata_dict.update({"page": 0})
        self.metadata_dict.update({"filename": bookname})
        text_with_metadata.append(Document(
                page_content=self.summary,
                metadata=self.metadata_dict.copy()
            ))

        return text_with_metadata

    def get_vectors_by_filename(self, filename):
        # Establish a direct connection to the database
        conn = psycopg2.connect(self.psycopg2_connection)
        cursor = conn.cursor()

        # Query to fetch all data where metadata->>'filename' matches the specified filename
        fetch_query = """
        SELECT id, embedding, cmetadata FROM public.langchain_pg_embedding
        WHERE cmetadata->>'filename' = %s
        """
        cursor.execute(fetch_query, (filename,))
        rows = cursor.fetchall()

        # Commit the transaction and close the connection
        conn.commit()
        cursor.close()
        conn.close()

        return rows

    def update_metadata_with_predicted_label(self, filename):
        # Fetch the vectors and metadata
        vectors = self.get_vectors_by_filename(filename)

        if not vectors:
            print(f"No vectors found with filename: {filename}")
            return

        # Prepare for update
        updated_count = 0

        # Establish a new connection for the update
        conn = psycopg2.connect(self.psycopg2_connection)
        cursor = conn.cursor()

        for row in vectors:
            record_id, embedding, metadata = row

            if isinstance(metadata, str):
                metadata_dict = json.loads(metadata)
            else:
                metadata_dict = metadata

            try:
                # print(f"Processing embedding for record {record_id}")
                # print(f"Embedding type: {type(embedding)}")

                # Convert embedding string to a numpy array
                embedding_np = np.array(ast.literal_eval(embedding))  # Use ast.literal_eval to convert string to list
                # print(f"Numpy array shape: {embedding_np.shape}")
                # print(f"Numpy array dtype: {embedding_np.dtype}")

                # Reshape the embedding
                embedding_reshaped = embedding_np.reshape(1, -1)
                # print(f"Reshaped array shape: {embedding_reshaped.shape}")

                # Predict label for individual embedding
                predicted_label = self.svm_model.predict(embedding_reshaped)[0]

                # Update metadata with predicted label
                metadata_dict['label'] = predicted_label

                # Update the database
                update_query = """
                UPDATE public.langchain_pg_embedding
                SET cmetadata = %s
                WHERE id = %s
                """
                cursor.execute(update_query, (json.dumps(metadata_dict), record_id))
                updated_count += 1
                # print(f"Successfully updated record {record_id}")

            except Exception as e:
                print(f"Error processing embedding for record {record_id}: {str(e)}")
                continue

        # Commit the transaction and close the connection
        conn.commit()
        cursor.close()
        conn.close() 
        print(f"ADD lable on metadata Successfully")
        
        
    def delete_vectors_by_filename_sql(self, filename):
        # Establish a direct connection to the database
        conn = psycopg2.connect(self.psycopg2_connection)
        cursor = conn.cursor()

        # Count how many rows will be affected
        count_query = """
        SELECT COUNT(*) FROM public.langchain_pg_embedding
        WHERE cmetadata->>'filename' = %s
        """
        cursor.execute(count_query, (filename,))
        count = cursor.fetchone()[0]

        # Delete the rows
        delete_query = """
        DELETE FROM public.langchain_pg_embedding
        WHERE cmetadata->>'filename' = %s
        """
        cursor.execute(delete_query, (filename,))

        # Commit the transaction and close the connection
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Deleted {count} vectors with filename: {filename}")

    def process_pdf(self, pdf_path, bookname):
        # Main execution flow
        pdf_content = self.read_pdf(pdf_path)
        meaningful_chunks = self.create_meaningful_chunks(pdf_content)

        # Split the content
        self.summary, metadata = self.split_content(meaningful_chunks)
        self.metadata_dict = self.extract_metadata(metadata)
        pdf_text_with_metadata = self.extract_text_from_pdf(pdf_path, bookname)

        doc_ids = [str(uuid.uuid4()) for _ in pdf_text_with_metadata]

        # Data insertion
        print("Started data insertion")
        self.vectorstore.add_documents(pdf_text_with_metadata, ids=doc_ids)
        print("Data insertion complete")
        self.update_metadata_with_predicted_label(bookname)
        print("Data lablling complete")

# # Usage
# if __name__ == "__main__":
#     pdf_processor = PDFProcessor()
#     ve=pdf_processor.get_vectors_by_filename("New-HCV _Volume 1")
#     with open('pdf_page_labels22.json', 'w') as f:
#         json.dump(ve, f, indent=4)
#     pdf_processor.update_metadata_with_predicted_label("New-HCV _Volume 1")

    # pdf_path = "ha.pdf"
    # extracted_text = pdf_processor.read_pdf(pdf_path)
    # print(extracted_text)
    # pdf_processor.process_pdf(pdf_path, "Sample Book Name")