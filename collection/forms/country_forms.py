from django import forms
from ..models import Country

class CountryForm(forms.ModelForm):
    """Form for creating and editing countries"""
    
    class Meta:
        model = Country
        fields = ['name', 'full_name', 'short_name', 'description', 'note']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country code (e.g. US, DE, RU)'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full country name'}),
            'short_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional short name or abbreviation'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Description of this country'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Notes about this country'}),
        }
        labels = {
            'name': 'Country Code/Name',
            'full_name': 'Full Country Name',
            'short_name': 'Short Name',
            'description': 'Description',
            'note': 'Notes',
        }
        help_texts = {
            'name': 'Required. Code or short name used to identify this country (e.g. US, Germany).',
            'full_name': 'Optional. The complete name of the country.',
            'short_name': 'Optional. An abbreviated name or code, if different from the primary name.',
            'description': 'Optional. Describe the time period and geopolitical boundaries this country represents, to define which artifacts fall under it.',
            'note': 'Optional. Additional information about this country. Use double braces {{ }} around confidential notes.',
        }
