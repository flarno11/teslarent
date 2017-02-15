from django import forms

from teslarent.models import Rental
from .models import Credentials


# no ModelForm since we allow existing email address to be entered again
class CredentialsForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class RentalForm(forms.ModelForm):
    class Meta:
        model = Rental
        fields = ['start', 'end', 'vehicle', 'description', 'code']
        widgets = {'code': forms.HiddenInput()}
