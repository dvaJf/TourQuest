
from django.forms import ModelForm, TextInput, Textarea,DateInput,ChoiceField
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User=get_user_model()
class UserCreationForm1(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User