from django.forms import ModelForm, TextInput

from .models import User


class NewUserForm(ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "phone", "password"]
        labels = ""
        help_texts = {
            "username": ""
        }
        widgets = {
            "username": TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
            "first_name": TextInput(attrs={"class": "form-control", "placeholder": "First Name"}),
            "last_name": TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}),
            "email": TextInput(attrs={"class": "form-control", "placeholder": "Email"}),
            "phone": TextInput(attrs={"class": "form-control", "placeholder": "Phone Number"}),
            "password": TextInput(attrs={"class": "form-control", "type": "password", "placeholder": "Password"})
        }
