from django import forms
from recommender.models import Profile


class ProfileForm(forms.ModelForm):

    class Meta:
        model = Profile

        fields = [
            "phone",
            "bio",
            "education",
            "experience",
            "skills",
            "preferred_location",
            "expected_salary",
            "resume",
            "profile_picture",
        ]

        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Tell employers about yourself"
                }
            ),

            "skills": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Example: Python, Django, SQL"
                }
            ),
        }