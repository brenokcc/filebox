from django import forms
from .models import File
from django.contrib.auth.models import User


class UploadFileForm(forms.ModelForm):
    class Meta:
        model = File
        fields = 'name',  'file'

class LoginForm(forms.Form):
    email = forms.EmailField(label='E-mail')
    password = forms.CharField(label='Password', widget=forms.PasswordInput())

    def submit(self):
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        user = User.objects.filter(username=email).first()
        if user:
                return user, user.check_password(password)
        else:
                return User.objects.create_user(email, email, password), True
