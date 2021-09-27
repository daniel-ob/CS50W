from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ModelForm, Textarea


class User(AbstractUser):
    pass


class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    text = models.CharField(max_length=512, blank=False)
    creation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} says '{self.text}'"


class NewPostForm(ModelForm):
    """Create form from Post model"""

    class Meta:
        model = Post
        fields = ["text"]
        labels = {
            "text": ""
        }
        widgets = {
            "text": Textarea(attrs={
                "autofocus": "",
                "rows": 2,
                "class": "form-control",
                "placeholder": "What's new?"
            })
        }
