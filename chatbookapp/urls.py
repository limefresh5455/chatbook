from django.urls import path
from chatbookapp.auth.views import *
from chatbookapp.chat.chat import *
from chatbookapp.chat.book import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    
    #authentication urls API
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),
    path('api/auth/resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('api/auth/login/', LoginView.as_view(), name='loginapi'),
    path('api/auth/forget-password/', ForgotPasswordView.as_view(), name='forget-password'),
    path('api/auth/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('api/auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('api/auth/google-signin/', GoogleSigninView.as_view(), name='google-signin'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('api/auth/profile/<int:user_id>/', ProfileAPIView.as_view(), name='profile'),
    path('api/profile/getUser-profile/', GetUserProfileAPI.as_view(), name='get-profile'),
    path('api/profile/updateUser-image/', UpdateUserProfileAPI.as_view(), name='update-profile'),
    ####################
    
    #chat urls API
    #website urls API
    path('api/get-book/', index, name='index'),
    path('api/get-subscribed-books/', subscribed_books, name='subscribed_books'),
    
    #mobile  apis urls
    
    path('api/get-books/', get_books, name='get-books'), 
    path('api/search-books/', SearchBookListView.as_view(), name='search-book-list'),
    
    # path('api/get-books-pagination/', BookListView.as_view(), name='get-books-pagination'),
    # path('api/books/genres/', BookGenreView.as_view(), name='book-genre-list'),
    # path('api/books/by-price/', BookPriceRangeView.as_view(), name='books-by-price'),
    # path('api/books/by-author/', BookAuthorView.as_view(), name='books-by-author'),
    # path('api/chat/', chat, name='chat'),
    
    #comman Mobile and web apis urls
    path("api/chat/",ChatView.as_view(),name="chat-main"),
    path('api/delete-book/<int:book_id>/', delete_book_api, name='delete_book_api'),
    
    # path('api/select-book/', select_book, name='select_book'),
    # path('api/select-language/', select_language, name='select_language'),
    # path('api/upload-folder/', upload_folder, name='upload_folder'),
    # path('api/upload-file/', upload_file, name='upload-file'),
    
    # path('api/add-book-library/', add_book_to_library, name='add_book_to_library'),
    # path('api/add-book-cart/', add_book_to_cart, name='add_book_to_cart'),
    
    ########################
    
    #plan API URLS
    
    path('api/payment/payment_success/', BuyBookAPIView.as_view(), name='buy-book'),
    path('api/book/<int:book_id>/', BookDetailView.as_view(), name='book-detail'),
    path('api/subscribed-books/', GetSubscribedBooksAPIView.as_view(), name='subscribed-books'),
    path('api/subscription-status/<int:subscription_id>/', SubscriptionStatusView.as_view(), name='subscription-status'),
    # path('api/payment/upgrade-plan/', UpgradePlanAPIView.as_view(), name='upgrade-plan'),
    #########################
    #function
    
    path('upload-file/', upload_file_function, name='upload'),
    # path('download-stopwords/', download_stopwords, name='download_stopwords'),
    
]
