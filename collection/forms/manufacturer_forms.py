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

class ManufacturerMoveForm(forms.Form):
    new_country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        label="New Country",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, caliber=None, **kwargs):
        super().__init__(*args, **kwargs)
        if caliber:
            self.fields['new_country'].queryset = Country.objects.filter(caliber=caliber)
            
