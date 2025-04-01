from django import forms
from ..models import Manufacturer, Country

class ManufacturerForm(forms.ModelForm):
    """Form for creating and editing manufacturers"""
    
    class Meta:
        model = Manufacturer
        fields = ['code', 'name', 'note']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manufacturer code (e.g. WIN, REM)'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full manufacturer name'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Notes about this manufacturer'}),
        }
        labels = {
            'code': 'Manufacturer Code',
            'name': 'Manufacturer Name',
            'note': 'Notes',
        }
        help_texts = {
            'code': 'Required. Short code used to identify this manufacturer (e.g. WIN, REM).',
            'name': 'Optional. The complete name of the manufacturer.',
            'note': 'Optional. Additional information about this manufacturer. Use double braces &#123;&#123; &#125;&#125; around confidential notes.',
        }
