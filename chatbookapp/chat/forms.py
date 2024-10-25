from django import forms
from chatbookapp.models import Book,Profile
from django.core.exceptions import ValidationError

# class BookForm(forms.ModelForm):
#     class Meta:
#         model = Book
#         fields = ['book_name', 'image', 'pdf']


class FolderUploadForm(forms.Form):
    folder = forms.FileField(widget=forms.ClearableFileInput(attrs={'webkitdirectory': True, 'directory': True}))


class FileUploadForm(forms.Form):
    file = forms.FileField()
    selling_price = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'placeholder': 'Enter price'}))  # Renamed to price

    # selling_price = forms.FloatField(required=False)
    
class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['book_name', 'author_name',  'pdf', 'selling_price', 'book_genre']  # Include all fields you want in the form

    # You can customize widgets if needed
    selling_price = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'placeholder': 'Enter price'}))
    
    

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['username', 'email', 'first_name', 'last_name', 'avatar']

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large ( > 5mb )")
        return avatar