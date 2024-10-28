from rest_framework.decorators import api_view, permission_classes,authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from django.http import StreamingHttpResponse
from django.core.cache import cache
from .search import BookAssistant
from chatbookapp.models import *
from .upload_pdfs import process_pdf, handle_uploaded_file
import json
import os
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .forms import BookForm, FolderUploadForm,FileUploadForm
from django.shortcuts import render,get_object_or_404
from .insert_pdf_vectore import PDFProcessor
from django.shortcuts import redirect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import asyncio
from asgiref.sync import sync_to_async
import threading
import time
from django.contrib.sessions.backends.db import SessionStore
from django.db.models import Q

from .serializers import BookSerializer
        
import nltk
from django.http import JsonResponse
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q
from rest_framework import generics
from .serializers import BookSerializer
from rest_framework.exceptions import NotFound
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.utils.decorators import method_decorator
from django.db.models import Count
from botocore.exceptions import ClientError

import boto3
from django.conf import settings
assistant = BookAssistant()
processor = PDFProcessor()
        
        
#################################
def download_stopwords(request):
    # Download stopwords if not already downloaded
    try:
        nltk.download('stopwords')
        return JsonResponse({'status': 'Stopwords downloaded successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'Error downloading stopwords.', 'error': str(e)})        
#############################    
        
from functools import wraps

def skip_ngrok_warning(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        response['ngrok-skip-browser-warning'] = 'true'
        return response
    return wrapped_view


##############################

@skip_ngrok_warning
@api_view(['GET'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
def index(request):
    # Fetch all books
    books = Book.objects.all()

    book_details = [
            {
                "uuid": book.uuid,
                "id": book.id,
                'name': book.book_name,
                'auther_name': book.author_name,
                'image': book.image.url if book.image else None,
                'pdf': book.pdf.url if book.pdf else None
            } for book in books
        ]
    print("BOOOKK")
    return Response({
        'books': book_details,
    })

##################
@api_view(['GET'])
@authentication_classes([JWTAuthentication])  
@permission_classes([IsAuthenticated])  
def subscribed_books(request):
    # Get the authenticated user's profile ID
    profile = request.user.id
    
    # Fetch the user's subscriptions (assuming you track subscriptions with a profile FK)
    user_subscriptions = Subscription.objects.filter(profile=profile, plan_type__in=["LEARNER", "EXAMINER"])

    # Get only the books associated with the user's subscriptions
    subscribed_books = [sub.book for sub in user_subscriptions]
    
    # Format the book details
    book_details = [
        {
            "uuid": book.uuid,
            "id": book.id,
            'name': book.book_name,
            'author_name': book.author_name,
            'image': book.image.url if book.image else None,
            'pdf': book.pdf.url if book.pdf else None,
            'book_genre': book.book_genre
        } for book in subscribed_books
    ]
    
    # Return the list of subscribed books
    return Response({
        'subscribed_books': book_details,
    })
#########################################


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_books(request):
    # Fetch all books
    
    books = Book.objects.all()[:10]
    recommended_books = Book.objects.order_by('?')[:10]
    trending_books=Book.objects.order_by('?')[:10]
    
    # Fetch user's subscriptions
    profile = Profile.objects.get(id=request.user.id)
    # user_Basic_subscriptions = Subscription.objects.filter(profile=profile,plan_type__in=["BASIC"])
    user_subscriptions = Subscription.objects.filter(profile=profile, plan_type__in=["LEARNER", "EXAMINER"])
    
    subscribed_book_ids = set(sub.book.id for sub in user_subscriptions)
    
    book_details = [
        {
            "uuid": book.uuid,
            "id": book.id,
            'name': book.book_name,
            'auther_name': book.author_name,
            'image': book.image.url if book.image else None,
            'pdf': book.pdf.url if book.pdf else None,
            'book_genre':book.book_genre
        } for book in books if book.id not in subscribed_book_ids
    ]
    
    recommend_books_details = [
        {
            "uuid": book.uuid,
            "id": book.id,
            'name': book.book_name,
            'auther_name': book.author_name,
            'image': book.image.url if book.image else None,
            'pdf': book.pdf.url if book.pdf else None,
            'book_genre':book.book_genre
            
        } for book in recommended_books if book.id not in subscribed_book_ids
    ]
    
    tranding_books_details = [
        {
            "uuid": book.uuid,
            "id": book.id,
            'name': book.book_name,
            'auther_name': book.author_name,
            'image': book.image.url if book.image else None,
            'pdf': book.pdf.url if book.pdf else None,
            'book_genre':book.book_genre
            
        } for book in trending_books if book.id not in subscribed_book_ids
    ]

    
    subscription_details = [
        {
            "book": {
                "uuid": sub.book.uuid,
                "id": sub.book.id,
                "name": sub.book.book_name,
                'auther_name': sub.book.author_name,
                'image': sub.book.image.url if sub.book.image else None,
                'pdf': sub.book.pdf.url if sub.book.pdf else None,
                'book_genre':sub.book.book_genre
                
            }
        } for sub in user_subscriptions
    ]

    return Response({
        'books': book_details,
        'subscriptions': subscription_details,
        "recommended_books":recommend_books_details,
        "tranding_books":tranding_books_details,
    })

##################################




class SearchBookListView(generics.ListAPIView):
    """
    API view to list books with optional search and genre filtering.
    This view supports:
    - Searching by book name via `search` query parameter
    - Filtering by genres via `genres` query parameter
    - Pagination via `limit` and `offset` query parameters    
    """
    
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = BookSerializer

    def get_queryset(self):
        search = self.request.query_params.get('search', None)
        genres = self.request.query_params.getlist('genres')
        queryset = Book.objects.all().order_by('-created_at')
        
        # Search by book name
        if search:
            queryset = queryset.filter(book_name__icontains=search)
        
        # Filter by genres
        if genres:
            genre_queries = [Q(book_genre__icontains=genre.strip()) for genre in genres]
            combined_query = Q()
            for query in genre_queries:
                combined_query |= query
            queryset = queryset.filter(combined_query)
            
         # Exclude books that the user is subscribed to
        profile = Profile.objects.get(id=self.request.user.id)
        user_subscriptions = Subscription.objects.filter(profile=profile, plan_type__in=["LEARNER", "EXAMINER"])
        subscribed_book_ids = set(sub.book.id for sub in user_subscriptions)
        queryset = queryset.exclude(id__in=subscribed_book_ids)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        try:
            page = self.paginate_queryset(queryset)
        except NotFound:
            return Response({'books': []}, status=200)

        # Prepare the response with paginated or full book list
        if page is not None:
            book_details = [
                {
                    "uuid": book.uuid,
                    "id": book.id,
                    'name': book.book_name,
                    'auther_name': book.author_name,
                    'image': book.image.url if book.image else None,
                    'pdf': book.pdf.url if book.pdf else None,
                    'book_genre': book.book_genre
                } for book in page
            ]
            return self.get_paginated_response({'books': book_details})

        book_details = [
            {
                "uuid": book.uuid,
                "id": book.id,
                'name': book.book_name,
                'auther_name': book.author_name,
                'image': book.image.url if book.image else None,
                'pdf': book.pdf.url if book.pdf else None,
                'book_genre': book.book_genre
            } for book in queryset
        ]
        return Response({'books': book_details})

##################################


class BookListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Book.objects.all().order_by('-created_at')
    serializer_class = BookSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        try:
            page = self.paginate_queryset(queryset)
        except NotFound:
            return Response({'books': []}, status=200)
        
        if page is not None:
            book_details = [
                {
                    "uuid": book.uuid,
                    "id": book.id,
                    'name': book.book_name,
                    'author_name': book.author_name,
                    'image': book.image.url if book.image else None,
                    'pdf': book.pdf.url if book.pdf else None,
                    'book_genre': book.book_genre
                } for book in page
            ]
            return self.get_paginated_response({'books': book_details})

        book_details = [
            {
                "uuid": book.uuid,
                "id": book.id,
                'name': book.book_name,
                'author_name': book.author_name,
                'image': book.image.url if book.image else None,
                'pdf': book.pdf.url if book.pdf else None,
                'book_genre': book.book_genre
            } for book in queryset
        ]
        return Response({'books': book_details})

####################

class BookGenreView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        genres = request.query_params.getlist('genres')  # Get genres from query parameters
        
        if not genres:
            return Response({"error": "No genres provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create a Q object for each genre
        genre_queries = [Q(book_genre__icontains=genre.strip()) for genre in genres]
        
        # Combine all Q objects with OR operator
        combined_query = Q()
        for query in genre_queries:
            combined_query |= query
        
        # Fetch books that match any of the genres
        books = Book.objects.filter(combined_query)
        
        # Prepare the response data directly from the queryset
        book_genre_details=[
            {
                "uuid": book.uuid,
                "id": book.id,
                'name': book.book_name,
                'author_name': book.author_name,
                'image': book.image.url if book.image else None,
                'pdf': book.pdf.url if book.pdf else None,
                'book_genre': book.book_genre
             } for book in books
            ]
        return Response({
        'books': book_genre_details,
        })
    
######################
class BookPriceRangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        
        if min_price is None or max_price is None:
            return Response({"error": "Both min_price and max_price must be provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            min_price = float(min_price)
            max_price = float(max_price)
        except ValueError:
            return Response({"error": "Invalid price values."}, status=status.HTTP_400_BAD_REQUEST)
        
        books = Book.objects.filter(selling_price__gte=min_price, selling_price__lte=max_price)
        
        book_price_details = [
            {
                "id": book.id,
                "book_name": book.book_name,
                "author_name": book.author_name,
                "genre": book.book_genre,
                "selling_price": book.selling_price,
                "image": book.image.url if book.image else None,
                "pdf": book.pdf.url if book.pdf else None
            } for book in books
        ]
        
        return Response({
            "books": book_price_details,
        })


###################
class BookAuthorView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        authors = request.query_params.getlist('authors')
        
        if not authors:
            return Response({"error": "No authors provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        author_queries = [Q(author_name__icontains=author.strip()) for author in authors]
        
        combined_query = Q()
        for query in author_queries:
            combined_query |= query
        
        books = Book.objects.filter(combined_query)
        
        book_author_details = [
            {
                "id": book.id,
                "book_name": book.book_name,
                "author_name": book.author_name,
                "genre": book.book_genre,
                "selling_price": book.selling_price,
                "image": book.image.url if book.image else None,
                "pdf": book.pdf.url if book.pdf else None
            } for book in books
        ]
        
        return Response({
            "books": book_author_details,
        })   


###########

################



#######################
class ChatView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_profile(self, user):
        """Helper method to fetch user profile."""
        try:
            return Profile.objects.get(id=user.id)
        except Profile.DoesNotExist:
            return None
        
    def get_or_create_subscription(self, profile, book_name):
        """Fetch user's subscription for the given book or create a free subscription if possible."""
        try:
            book = Book.objects.get(book_name=book_name)
            subscription = Subscription.objects.filter(profile=profile, book=book).first()
            
            if subscription:
                return subscription
            
            # Check if user already has 5 BASIC subscriptions
            # basic_sub_count = Subscription.objects.filter(profile=profile, plan_type='BASIC').count()
            
            # if basic_sub_count >= 5:
            #     return None  # User has reached the limit for BASIC subscriptions
            
            # Create a new BASIC subscription
            subscription = Subscription.objects.create(
                profile=profile,
                book=book,
                plan_type='BASIC',
                duration='MONTHLY',
                price=0,
                start_date=timezone.now().date(),
                end_date=timezone.now().date() + relativedelta(months=1)
            )
            return subscription
        except Book.DoesNotExist:
            return None
        
    def get_subscription(self, profile, book_name):
        """Fetch user's subscription for the given book."""
        try:
            book = Book.objects.get(book_name=book_name)
            return Subscription.objects.get(profile=profile, book=book)
        except (Book.DoesNotExist, Subscription.DoesNotExist):
            return None

    def clean_chat_history(self, chat_history):
        """Helper method to process and clean chat history."""
        if not chat_history:
            return '[]'  # Initialize as empty list in JSON format
        chat_history = json.loads(chat_history)
        chat_history = [{k: v for k, v in message.items() if k != 'image'} for message in chat_history]
        return json.dumps(chat_history)

    def event_stream(self, user_input, image_path, page_no, book_name, language, chat_history):
        """Helper method to stream the response from the assistant."""
        response = ""
        for chunk in assistant.query(user_input, image_path, page_no, book_name, language, chat_history):
            response += chunk
            yield f"data: {chunk}\n\n"

    def check_subscription_validity(self, subscription):
        """Check if the subscription is valid and not expired."""
        if subscription and subscription.is_expired():
            return False
        return True

    # def get(self, request):
    #     """Handle GET requests."""
    #     profile = self.get_profile(request.user)
    #     if not profile:
    #         return Response({
    #             'error': 'User profile not found'
    #         }, status=status.HTTP_404_NOT_FOUND)

    #     user_input = request.query_params.get('message', '')
    #     image_path = request.query_params.get('image_path', None)
    #     page_no = request.query_params.get('page_no', 0)
    #     book_name = request.query_params.get('book_name')
    #     chat_history = request.query_params.get('chat_history')
    #     language = request.query_params.get('language', "English")

    #     chat_history = self.clean_chat_history(chat_history)

    #     # Fetch the user's subscription
    #     subscription = self.get_or_create_subscription(profile, book_name)
    #     # subscription = self.get_subscription(profile, book_name)
    #     if not subscription:
    #         return Response({
    #             'error': 'Please Subscribe.'
    #         }, status=status.HTTP_404_NOT_FOUND)

    #     # Check if the subscription is valid
    #     if not self.check_subscription_validity(subscription):
    #         return Response({
    #             'error': 'Your subscription has expired.'
    #         }, status=status.HTTP_403_FORBIDDEN)

    #     # Check if the user can ask a question
    #     if not subscription.can_ask_question():
    #         return Response({
    #             'error': 'You have reached your question limit for this subscription.'
    #         }, status=status.HTTP_403_FORBIDDEN)

    #     # Increment the question count
    #     subscription.increment_question_count()

    #     # Debugging logs
    #     print("PAGE", page_no)
    #     print("CHATHISTORY", chat_history)

    #     response = StreamingHttpResponse(self.event_stream(user_input, image_path, page_no, book_name, language, chat_history), content_type='text/event-stream')
    #     response['X-Accel-Buffering'] = 'no'
    #     return response




    def post(self, request):
        """Handle POST requests."""
        profile = self.get_profile(request.user)
        if not profile:
            return Response({
                'status': 'error',
                'profile': 'User profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

        user_input = request.data.get('message', '')
        image_path = request.data.get('image_path', None)
        page_no = request.data.get('page_no', 0)
        book_name = request.data.get('book_name')
        chat_history = request.data.get('chat_history')
        language = request.data.get('language')

        chat_history = self.clean_chat_history(chat_history)

        # Fetch the user's subscription
        # subscription = self.get_subscription(profile, book_name)
        subscription = self.get_or_create_subscription(profile, book_name)
        if not subscription:
            return Response({
                'error': 'Please Subscribe'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if the subscription is valid
        if  subscription.is_expired():
            return Response({
                'error': f'Your subscription has expired on date {subscription.end_date} .'
                
            }, status=status.HTTP_409_CONFLICT)

        # Check if the user can ask a question
        if not subscription.can_ask_question():
            return Response({
                'error': 'You have reached your question limit for this subscription.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Increment the question count
        subscription.increment_question_count()

        # Debugging logs
        print("PAGE", page_no)
        print("CHATHISTORY", chat_history)
        print("LANGUAGE", language)

        response = StreamingHttpResponse(self.event_stream(user_input, image_path, page_no, book_name, language, chat_history), content_type='text/event-stream')
        response['X-Accel-Buffering'] = 'no'
        return response

#############################


    
@api_view(['POST'])
@permission_classes([IsAdminUser])
def upload_folder(request):
    form = FolderUploadForm(request.POST, request.FILES)
    if form.is_valid():
        files = request.FILES.getlist('folder')
        for file in files:
            if file.name.endswith('.pdf'):
                pdf_path = handle_uploaded_file(file)
                process_pdf(pdf_path, file.name)
                os.unlink(pdf_path)
        return Response({'status': 'success', 'message': 'Files uploaded successfully'}, status=status.HTTP_201_CREATED)
    return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


##################################

@api_view(['POST'])
@permission_classes([IsAdminUser])
def upload_file(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            if file.name.endswith('.pdf'):
                pdf_path = handle_uploaded_file(file)
                process_pdf(pdf_path, file.name)
                # Remove the temporary file after processing
                os.unlink(pdf_path)
            return redirect('index')
    else:
        form = FileUploadForm()
    return render(request, 'upload_book.html', {'form': form})

##################################
@api_view(['DELETE'])
@csrf_exempt
# @permission_classes([IsAuthenticated])
def delete_book_api(request, book_id):
    
    book = get_object_or_404(Book, id=book_id)
    
    # Initialize the PDFProcessor
    processor = PDFProcessor()
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    # Delete the book's PDF file from S3
    if book.pdf:
        pdf_key = book.pdf.name  # Get the S3 key (file path) from the book model
        try:
            s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=pdf_key)
        except ClientError as e:
            return Response({"detail": f"Error deleting PDF from S3: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Delete the book's image from S3
    if book.image:
        image_key = book.image.name  # Get the S3 key (file path) from the book model
        try:
            s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=image_key)
        except ClientError as e:
            return Response({"detail": f"Error deleting image from S3: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Delete from vector database
    processor.delete_vectors_by_filename_sql(book.book_name)

    # Delete the book record from the RDS database
    book.delete()
    # Delete the book's PDF file and image from storage
    # if book.pdf and book.pdf.path:
    #     if os.path.isfile(book.pdf.path):
    #         os.remove(book.pdf.path)
    # if book.image and book.image.path:
    #     if os.path.isfile(book.image.path):
    #         os.remove(book.image.path)

    # Delete from vector database
    # processor.delete_vectors_by_filename_sql(book.book_name)

    # # Delete the book record from the database
    # book.delete()

    # Return a success response
    return Response({"detail": "Book deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

####################################################

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def select_book(request):
    try:
        # Explicitly fetching the Profile by user ID
        profile = Profile.objects.get(id=request.user.id)
        print("USERNMAE",profile.username)
        user_id = str(profile.user_id)
    except Profile.DoesNotExist:
        return Response({
            'status': 'error',
            'profile': 'User profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    session_id = request.session.get('chat_session_id')
    book_name = request.data.get('book')

    if not book_name:
        return Response({
            'status': 'error',
            'book': 'Book name is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        book = Book.objects.get(book_name=book_name)
        book_id = book.uuid
        assistant.set_current_book(user_id, session_id, book_name)
        return Response({
            'status': 'success',
            'book_id': str(book_id),
            'book': f'Book "{book_name}" selected successfully'
        })
    except Book.DoesNotExist:
        return Response({
            'status': 'error',
            'book': f'Book "{book_name}" not found'
        }, status=status.HTTP_404_NOT_FOUND)
        
##############################        
@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def select_language(request):
    try:
        # Explicitly fetching the Profile by user ID
        profile = Profile.objects.get(id=request.user.id)
        # profile = request.user
        print("USERNMAE",profile.username)
        user_id = str(profile.user_id)
    except Profile.DoesNotExist:
        return Response({
            'status': 'error',
            'profile': 'User profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    session_id = request.session.get('chat_session_id')
    language = request.data.get('language')

    if not language:
        return Response({
            'status': 'error',
            'language': 'Language is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    assistant.set_current_language(user_id, session_id, language)
    return Response({
        'status': 'success',
        'language': language,
        'message': f'"{language}" selected successfully'
    })


#########   #####################
########################API######################################
###########################API###################################












#####################Only functions############################

from django.shortcuts import render,get_object_or_404
# Create your views here.
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required

# Create your views here.
from django.shortcuts import render
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from .search import BookAssistant  # Import your query function
from django.contrib.auth import logout
from django.shortcuts import redirect
from chatbookapp.models import Book
from django.core.cache import cache
import json
from django.views.decorators.http import require_POST
from .upload_pdfs import process_pdf, handle_uploaded_file
import os
from .insert_pdf_vectore import PDFProcessor
from django.contrib.auth.decorators import user_passes_test
import os
import tempfile
from io import BytesIO
from django.shortcuts import render, redirect
from django.core.files import File
from django.contrib.auth.decorators import login_required, user_passes_test
from PIL import Image
import fitz
from chatbookapp.models import Book
from .insert_pdf_vectore import PDFProcessor
from .forms import FileUploadForm



def is_admin(user):
    return user.is_staff 
# #########################################

# ###########################

# @login_required(redirect_field_name="")
# @user_passes_test(is_admin)
# def upload_file_function(request):
#     if request.method == 'POST':
#         form = BookForm(request.POST, request.FILES)
#         if form.is_valid():
#             book = form.save(commit=False)
#             file = form.cleaned_data['file']
#             selling_price = form.cleaned_data['selling_price']
            
#             if file.name.endswith('.pdf'):
#                 # Create a temporary file to store the uploaded PDF
#                 with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
#                     for chunk in file.chunks():
#                         temp_file.write(chunk)
#                 pdf_path = temp_file.name

#                 # Process the PDF
#                 doc = fitz.open(pdf_path)
                
#                 if len(doc) > 0:
#                     page = doc.load_page(0)  # Load the first page
#                     pix = page.get_pixmap()  # Render page to an image
                    
#                     # Convert pixmap to image
#                     img_data = pix.tobytes('png')
#                     img = Image.open(BytesIO(img_data))

#                     # Save image to a BytesIO object
#                     img_io = BytesIO()
#                     img.save(img_io, format='PNG')
#                     img_io.seek(0)

#                     # Create Book instance
#                     book = Book()
#                     book.book_name = os.path.splitext(file.name)[0]
#                     book.selling_price = selling_price  # Set the selling price
#                     print("@@@@@@@ this is book name", book.book_name)
                    
#                     # Save image and pdf
#                     book.image.save(f"{book.book_name}.png", File(img_io), save=False)
#                     book.pdf.save(file.name, File(open(pdf_path, 'rb')), save=False)
                    
#                     # Save the book instance to the database
#                     book.save()
#                     processor.process_pdf(pdf_path, book.book_name)
#                     print(f"Processed and saved: {file.name}")

#                 doc.close()

#                 # Remove the temporary file after processing
#                 os.unlink(pdf_path)
                
#                 return redirect('index')
#     else:
#         form = BookForm()
#     return render(request, 'upload_book.html', {'form': form})


@login_required(redirect_field_name="")
@user_passes_test(is_admin)
def upload_file_function(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            pdf_file = form.cleaned_data['pdf']
            
            if pdf_file.name.endswith('.pdf'):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    for chunk in pdf_file.chunks():
                        temp_file.write(chunk)
                    pdf_path = temp_file.name

                # Process the PDF
                doc = fitz.open(pdf_path)
                if len(doc) > 0:
                    page = doc.load_page(0)  # Load the first page
                    pix = page.get_pixmap()  # Render page to an image
                    img_data = pix.tobytes('png')
                    img = Image.open(BytesIO(img_data))

                    # Save image to a BytesIO object
                    img_io = BytesIO()
                    img.save(img_io, format='PNG')
                    img_io.seek(0)

                    # Save image and pdf
                    book.image.save(f"{book.book_name}.png", File(img_io), save=False)
                    book.pdf.save(pdf_file.name, File(open(pdf_path, 'rb')), save=False)

                    # Save the book instance to the database
                    book.save()

                    processor.process_pdf(pdf_path, book.book_name)
                    print(f"Processed and saved: {pdf_file.name}")

                doc.close()
                # Remove the temporary file after processing
                os.unlink(pdf_path)

                return redirect('index')
            else:
                form.add_error('pdf', 'Uploaded file must be a PDF.')
    else:
        form = BookForm()

    return render(request, 'upload_book.html', {'form': form})











######################## TEST API ####################

# class ChatView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get_profile(self, user):
#         """Helper method to fetch user profile."""
#         try:
#             profile = Profile.objects.get(id=user.id)
#             return str(profile.user_id)
#         except Profile.DoesNotExist:
#             return None

#     def clean_chat_history(self, chat_history):
#         """Helper method to process and clean chat history."""
#         if not chat_history:
#             return '[]'  # Initialize as empty list in JSON format
#         chat_history = json.loads(chat_history)
#         chat_history = [{k: v for k, v in message.items() if k != 'image'} for message in chat_history]
#         return json.dumps(chat_history)

#     def event_stream(self, user_input, image_path, page_no, book_name, language, chat_history):
#         """Helper method to stream the response from the assistant."""
#         response = ""
#         for chunk in assistant.query(user_input, image_path, page_no, book_name, language, chat_history):
#             response += chunk
#             yield f"data: {chunk}\n\n"

#     def get(self, request):
#         """Handle GET requests."""
#         user_id = self.get_profile(request.user)
#         if not user_id:
#             return Response({
#                 'status': 'error',
#                 'profile': 'User profile not found'
#             }, status=status.HTTP_404_NOT_FOUND)

#         user_input = request.query_params.get('message', '')
#         image_path = request.query_params.get('image_path', None)
#         page_no = request.query_params.get('page_no', 0)
#         book_name = request.query_params.get('book_name')
#         chat_history = request.query_params.get('chat_history')
#         language = request.query_params.get('language', "English")

#         chat_history = self.clean_chat_history(chat_history)

#         # Debugging logs
#         print("PAGE", page_no)
#         print("CHATHISTORY", chat_history)

#         response = StreamingHttpResponse(self.event_stream(user_input, image_path, page_no, book_name, language, chat_history), content_type='text/event-stream')
#         response['X-Accel-Buffering'] = 'no'
#         return response

#     def post(self, request):
#         """Handle POST requests."""
#         user_id = self.get_profile(request.user)
#         if not user_id:
#             return Response({
#                 'status': 'error',
#                 'profile': 'User profile not found'
#             }, status=status.HTTP_404_NOT_FOUND)

#         user_input = request.data.get('message', '')
#         image_path = request.data.get('image_path', None)
#         page_no = request.data.get('page_no', 0)
#         book_name = request.data.get('book_name')
#         chat_history = request.data.get('chat_history')
#         language = request.data.get('language')

#         chat_history = self.clean_chat_history(chat_history)

#         # Debugging logs
#         print("PAGE", page_no)
#         print("CHATHISTORY", chat_history)

#         response = StreamingHttpResponse(self.event_stream(user_input, image_path, page_no, book_name, language, chat_history), content_type='text/event-stream')
#         response['X-Accel-Buffering'] = 'no'
#         return response













