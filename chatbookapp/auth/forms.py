
from django import forms
from chatbookapp.models import Profile
from django.core.exceptions import ValidationError


# class ProfileForm(forms.ModelForm):
#     class Meta:
#         model = Profile
#         fields = ['username', 'email', 'first_name', 'last_name', 'avatar']

#     def clean_avatar(self):
#         avatar = self.cleaned_data.get('avatar')
#         if avatar:
#             if avatar.size > 5 * 1024 * 1024:
#                 raise ValidationError("Image file too large ( > 5mb )")
#         return avatar
    
    
class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['username',  'avatar']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Profile.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This email is already in use.")
        return email

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large ( > 5mb )")
        return avatar
