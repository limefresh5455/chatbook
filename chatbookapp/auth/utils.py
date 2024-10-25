import os
from datetime import datetime, timedelta
from typing import Union, Any

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.hashers import make_password, check_password

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def get_hashed_password(password: str) -> str:
    return make_password(password)

def verify_password(password: str, hashed_pass: str) -> bool:
    return check_password(password, hashed_pass)

def create_access_token(user):
    return RefreshToken.for_user(user).access_token

def create_refresh_token(user):
    return RefreshToken.for_user(user)

class JWTAuth(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        try:
            access_token = auth_header.split(' ')[1]
            payload = JWTAuthentication().get_validated_token(access_token)
        except AuthenticationFailed:
            raise AuthenticationFailed('Invalid token or expired token')

        user = JWTAuthentication().get_user(payload)
        return (user, None)

def get_current_user(request):
    auth = JWTAuth()
    user, _ = auth.authenticate(request)
    if user is None:
        raise AuthenticationFailed('User not found')
    return user

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': settings.SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}