from django.shortcuts import render
from chatbookapp.auth.otp_send import *
from chatbookapp.auth.utils import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from chatbookapp.models import *
from .serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.contrib.auth.hashers import make_password
import random
from rest_framework import viewsets, serializers
from rest_framework.decorators import api_view, permission_classes
from django.db import IntegrityError
from chatbookapp.models import Profile, OTP
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views import View
import json
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404

from .forms import ProfileForm

class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username', '')
        email = request.data.get('email', '')
        password = request.data.get('password', '')

        # Validate required fields
        if not username or not email or not password:
            return Response({"error": "Username, email, and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if email is valid (you can add more sophisticated validation here)
        if '@' not in email:
            return Response({"error": "Email is not valid."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already exists
        existing_user = Profile.objects.filter(email=email).first()
        if existing_user:
            if existing_user.is_verified:
                return Response({"error": "Email already exists and is verified."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # User exists but not verified, resend OTP
                return self.resend_otp(existing_user)

        # Create new user and send OTP for the first time
        return self.create_user_and_send_otp(username, email, password)

    def resend_otp(self, user):
        otp_code = self.generate_otp()
        email_check = resend_otp_email(user.email, otp_code,user.username)
        if email_check == "Email sent successfully":
            OTP.objects.filter(email=user.email).delete()
            OTP.objects.create(email=user.email, otp_code=otp_code)
            return Response({
                "message": "OTP resent for verification",
                "error": "An existing unverified account was found. We've sent a new OTP to your email."
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Failed to resend OTP email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_user_and_send_otp(self, username, email, password):
        hashed_password = make_password(password)
        try:
            user = Profile.objects.create(
                username=username,
                email=email,
                password=hashed_password,
                is_verified=False
            )
            return self.send_first_time_otp(user)
        except IntegrityError:
            return Response({"error": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)

    def send_first_time_otp(self, user):
        otp_code = self.generate_otp()
        email_check = send_otp_email(user.email, otp_code,user.username)
        if email_check == "Email sent successfully":
            OTP.objects.create(email=user.email, otp_code=otp_code)
            return Response({
                "message": "An OTP has been sent to your email for verification.",
                # "error": "An OTP has been sent to your email for verification."
            }, status=status.HTTP_201_CREATED)
        else:
            user.delete()  # Delete the user if email sending fails
            return Response({"error": "Failed to send OTP email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_otp(self):
        return ''.join([str(random.randint(0, 9)) for _ in range(4)])


class VerifyOtpView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp_code')
        
        try:
            otp = OTP.objects.get(email=email, otp_code=otp_code)
        except OTP.DoesNotExist:
            return Response({"error": "Invalid OTP or email."}, status=status.HTTP_400_BAD_REQUEST)

        if otp.expires_at < timezone.now():
            return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

        # Mark the user as verified
        try:
            user = Profile.objects.get(email=email)
            user.is_verified = True
            user.save()

            # Optionally, delete the OTP after successful verification
            otp.delete()

            return Response({"message": "OTP verified successfully. User is now verified."}, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)



@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        # Validate input
        if not email or not password:
            return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Profile.objects.get(email=email)
        except Profile.DoesNotExist:
            return Response({"error": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(password, user.password):
            return Response({"error": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_verified:
            return Response({"error": "Please verify your email address."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # Handle user subscription
        # try:
        #     user_subscription = UserSubscription.objects.get(user=user)
        #     subscription_plan = user_subscription.plan
        # except UserSubscription.DoesNotExist:
        #     subscription_plan = SubscriptionPlan.objects.get(name='free')
        #     user_subscription = UserSubscription.objects.create(user=user, plan=subscription_plan)

        # remaining_questions = user_subscription.daily_questions_remaining()

        # subscription_info = {
        #     'plan': subscription_plan.name,
        #     'daily_limit': {
        #         'free': 5,
        #         'basic': 100,
        #         'PRO': 'Unlimited'
        #     }.get(subscription_plan.name, 0),
        #     'remaining_questions': 'Unlimited' if remaining_questions == float('inf') else remaining_questions
        # }

        return Response({
            'refresh': str(refresh),
            'access_token': str(refresh.access_token),
            "user": {
                'id': user.id,
                'name': user.username,
                "email": user.email,
                "is_verified": user.is_verified
                # "subscription": subscription_info
            }
        }, status=status.HTTP_200_OK)



class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Profile.objects.get(email=email)
        except Profile.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Generate OTP
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])

        # Send OTP to user's email
        email_check = send_otp_email(user.email, otp_code,user.username)
        if email_check == "Email sent successfully":
        # Save OTP to the database
            OTP.objects.create(email=user.email, otp_code=otp_code)
            return Response({"message": "OTP sent to your email address."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Failed to send email. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class ResetPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        confirmPassword = request.data.get('confirmPassword')

        if not email or not new_password or not confirmPassword:
            return Response({"error": "Email, new password, and confirm password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirmPassword:
            return Response({"error": "New password and confirm password do not match."}, status=status.HTTP_400_BAD_REQUEST)

        # Reset the user's password
        try:
            user = Profile.objects.get(email=email)
            user.password = make_password(new_password)
            user.save()

            
            return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)



class ResendOTPView(APIView):
    def post(self, request):
        email = request.data.get('email', '')

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        user = Profile.objects.filter(email=email).first()

        if not user:
            return Response({"error": "No user found with this email."}, status=status.HTTP_404_NOT_FOUND)

        # if user.is_verified:
        #     return Response({"error": "User is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        return self.resend_otp(user)

    def resend_otp(self, user):
        otp_code = self.generate_otp()
        email_check = resend_otp_email(user.email, otp_code,user.username)
        
        if email_check == "Email sent successfully":
            OTP.objects.filter(email=user.email).delete()
            OTP.objects.create(email=user.email, otp_code=otp_code)
            return Response({
                "message": "OTP resent for verification",
                "detail": "A new OTP has been sent to your email."
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Failed to resend OTP email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_otp(self):
        return ''.join([str(random.randint(0, 9)) for _ in range(4)])






@method_decorator(csrf_exempt, name='dispatch')
class GoogleSigninView(APIView):
    def post(self, request):
        # Extract data directly from request.data
        authid = request.data.get('sub')
        name = request.data.get('name')
        email = request.data.get('email')

        # Check if required fields are present
        if not authid or not name or not email:
            return Response({
                'error': 'Missing required fields: sub, name, and email are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Handle Google sign-in logic
        signin_instance = SigninWithGoogle.handle_google_signin(authid, name, email)
        
        # If needed, generate tokens (uncomment these lines if you have implemented token handling)
        refresh = RefreshToken.for_user(signin_instance.profile)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return Response({
            'message': 'User signed in successfully',
            'access_token': access_token,
            'refresh_token': refresh_token,
            "user":{
            'id': signin_instance.profile.id,
            "email":signin_instance.profile.email,
            "name":signin_instance.profile.username,
            'is_verified': signin_instance.profile.is_verified
            }

        }, status=status.HTTP_200_OK)
        
  
        
class LogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"success": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_new_password = request.data.get('confirm_new_password')

        # Fetch the user's profile
        try:
            profile = Profile.objects.get(id=user.id)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not profile.check_password(old_password):
            return Response({'error': 'Old password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_new_password:
            return Response({'error': 'New passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        # Custom password validation
        try:
            validate_password(new_password, profile)
        except ValidationError as e:
            custom_errors = []
            for message in e.messages:
                if "too short" in message:
                    custom_errors.append("Your password must be at least 8 characters long.")
                elif "common" in message:
                    custom_errors.append("Your password is too common. Please choose a more unique password.")
                elif "entirely numeric" in message:
                    custom_errors.append("Your password cannot be entirely numeric.")
                else:
                    custom_errors.append(message)  # Keep other messages as is

            return Response({'error': custom_errors}, status=status.HTTP_400_BAD_REQUEST)

        profile.set_password(new_password)
        profile.save()

        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
    


class GetUserProfileAPI(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user  # This is already the Profile instance
        data = {
            'user_id': str(user.user_id),  # Convert UUID to string
            'username': user.username,
            'email': user.email,
            'is_verified': user.is_verified,
            'created_at': user.created_at,
            'avatar': user.avatar.url if user.avatar else None,
        }
        return Response(data)




 
class UpdateUserProfileAPI(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    ALLOWED_UPDATE_FIELDS = ['username', 'avatar']

    def clean_avatar(self, avatar):
        if avatar:
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large ( > 5mb )")
        return avatar

    def patch(self, request):
        user = request.user  # Already the Profile instance
        updated = False
        errors = {}

        # Update username if provided
        if 'username' in request.data:
            new_username = request.data.get('username')
            if new_username and new_username != user.username:
                # You might want to add more username validation here
                user.username = new_username
                updated = True

        # Update avatar if provided
        if 'avatar' in request.FILES:
            new_avatar = request.FILES.get('avatar')
            if new_avatar:
                try:
                    # Validate avatar
                    cleaned_avatar = self.clean_avatar(new_avatar)
                    user.avatar = cleaned_avatar
                    updated = True
                except ValidationError as e:
                    errors['avatar'] = str(e)

        if updated and not errors:
            try:
                user.save()
                response_data = {
                    'message': 'Profile updated successfully',
                    'data': {
                        'user_id': str(user.user_id),
                        'username': user.username,
                        'email': user.email,
                        'created_at': user.created_at,
                        'avatar': user.avatar.url if user.avatar else None,
                    }
                }
                return Response(response_data, status=status.HTTP_200_OK)
            except Exception as e:
                errors['general'] = str(e)
        elif not updated:
            errors['general'] = 'No valid fields to update were provided.'

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        
        
                
# class ProfileAPIView(APIView):
#     parser_classes = (MultiPartParser, FormParser, JSONParser)

#     def get(self, request, user_id):
#         try:
#             profile = Profile.objects.get(id=user_id)
#             data = {
#                 'username': profile.username,
#                 'email': profile.email,
#                 'first_name': profile.first_name,
#                 'last_name': profile.last_name,
#                 'avatar': profile.avatar.url if profile.avatar else None,
#             }
#             return Response(data)
#         except Profile.DoesNotExist:
#             return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
#     def patch(self, request, user_id):
#         try:
#             profile = Profile.objects.get(id=user_id)
            
#             # Get the current data of the profile
#             current_data = {
#                 'username': profile.username,
#                 'email': profile.email,
#                 'first_name': profile.first_name,
#                 'last_name': profile.last_name,
#             }

#             # Update the current data with the new data from the request
#             for field in current_data.keys():
#                 if field in request.data:
#                     current_data[field] = request.data[field]

#             # Handle avatar separately
#             if 'avatar' in request.FILES:
#                 current_data['avatar'] = request.FILES['avatar']
            
#             form = ProfileForm(current_data, instance=profile, files=request.FILES)
#             if form.is_valid():
#                 updated_profile = form.save()
#                 response_data = {
#                     'message': 'Profile updated successfully',
#                     'data': {
#                         'username': updated_profile.username,
#                         'email': updated_profile.email,
#                         'first_name': updated_profile.first_name,
#                         'last_name': updated_profile.last_name,
#                         'avatar': updated_profile.avatar.url if updated_profile.avatar else None,
#                     }
#                 }
#                 return Response(response_data)
#             else:
#                 return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)
#         except Profile.DoesNotExist:
#             return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)   
     
