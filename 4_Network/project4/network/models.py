from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ModelForm, Textarea


class User(AbstractUser):
    following = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="followers")


class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    text = models.CharField(max_length=512, blank=False)
    creation_date = models.DateTimeField(auto_now_add=True)
    liked_by = models.ManyToManyField("User", blank=True, related_name="likes")

    def __str__(self):
        return f"{self.author} says '{self.text}'"

    @property
    def likes_count(self):
        return self.liked_by.count()


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
