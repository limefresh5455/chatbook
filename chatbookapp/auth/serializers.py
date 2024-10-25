from rest_framework import serializers
from chatbookapp.models import *
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password


from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from chatbookapp.models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['user_id', 'username', 'email', 'password', 'is_verified', 'created_at']
        extra_kwargs = {
            'password': {'write_only': True},  # Password should not be readable
            'is_verified': {'read_only': True},  # Verification status is controlled internally
            'created_at': {'read_only': True}  # Auto-populated, should not be writable
        }

    def validate_password(self, value):
        """
        Hash the password before saving it to the database.
        """
        return make_password(value)

    def create(self, validated_data):
        # Create a new Profile instance
        profile = Profile.objects.create(**validated_data)
        return profile




class VerifyEmailSerializer(serializers.Serializer):
 email = serializers.EmailField()
 verification_token = serializers.UUIDField()



class LoginSerializer(serializers.Serializer):
 email = serializers.EmailField()
 password = serializers.CharField(write_only=True)

 def validate(self, data):
    email = data.get('email')
    password = data.get('password')

    try:
        user = Profile.objects.get(email=email)
    except Profile.DoesNotExist:
        raise serializers.ValidationError("Invalid email or password.")

    if not check_password(password, user.password):
        raise serializers.ValidationError("Invalid email or password.")

    if not user.is_verified:
        raise serializers.ValidationError("Please verify your email address.")

    data['user'] = user
    return data





# class SigninWithGoogleSerializer(serializers.ModelSerializer):
#     sub = serializers.CharField(max_length=255)
#     class Meta:
#         model = SigninWithGoogle
#         fields = ['sub', 'name', 'email']
