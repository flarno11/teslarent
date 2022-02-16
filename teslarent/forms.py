from django import forms

from teslarent.models import Rental


class CredentialsForm(forms.Form):
    email = forms.EmailField()


class TeslaAuthForm(forms.Form):
    email = forms.EmailField(widget=forms.HiddenInput())
    code_verifier = forms.CharField(widget=forms.HiddenInput())
    auth_code = forms.CharField()


class RentalForm(forms.ModelForm):
    class Meta:
        model = Rental
        fields = ['start', 'end', 'vehicle', 'description', 'code']
        widgets = {'code': forms.HiddenInput()}
