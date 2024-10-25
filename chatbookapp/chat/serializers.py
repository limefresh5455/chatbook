from rest_framework import serializers
from chatbookapp.models import Book, Profile

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'

# class CartMyLibrarySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Cart_My_Library
#         fields = '__all__'


