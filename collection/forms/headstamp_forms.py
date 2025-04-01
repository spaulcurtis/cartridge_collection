from django import forms
from ..models import Headstamp, Manufacturer, Source, HeadstampSource

class HeadstampForm(forms.ModelForm):
    """Form for creating and editing headstamps"""
    
    class Meta:
        model = Headstamp
        fields = ['code', 'name', 'primary_manufacturer', 'cc', 'note', 'image']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Headstamp code (e.g. FC 9mm)'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full headstamp name'}),
            'primary_manufacturer': forms.Select(attrs={'class': 'form-select'}),
            'cc': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Notes about this headstamp'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'code': 'Headstamp Code',
            'name': 'Headstamp Name',
            'primary_manufacturer': 'Case Manufacturer',
            'cc': 'Credibility Code',
            'note': 'Notes',
            'image': 'Headstamp Image',
        }
        help_texts = {
            'code': 'Required. Code as it appears on the headstamp.',
            'name': 'Optional. A more descriptive name for this headstamp.',
            'primary_manufacturer': 'Optional. The manufacturer who produced the case (if different from the main manufacturer).',
            'cc': 'Credibility of this information.',
            'note': 'Optional. Additional information about this headstamp. Use double braces &#123;&#123; &#125;&#125; around confidential notes.',
            'image': 'Optional. Upload an image of the headstamp.',
        }

    def __init__(self, manufacturer=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit primary_manufacturer choices to manufacturers in the same caliber
        if manufacturer:
            caliber = manufacturer.country.caliber
            self.fields['primary_manufacturer'].queryset = Manufacturer.objects.filter(
                country__caliber=caliber
            ).order_by('country__name', 'code')
            
            # Set the initial value to the current manufacturer
            if not self.instance.pk:  # Only for new instances
                self.initial['primary_manufacturer'] = manufacturer.pk

class HeadstampSourceForm(forms.ModelForm):
    """Form for adding sources to headstamps"""
    
    class Meta:
        model = HeadstampSource
        fields = ['source', 'date_sourced', 'note']
        widgets = {
            'source': forms.Select(attrs={'class': 'form-select'}),
            'date_sourced': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'source': 'Source',
            'date_sourced': 'Date Sourced',
            'note': 'Source Notes',
        }
        help_texts = {
            'source': 'Select a source for this headstamp information.',
            'date_sourced': 'Optional. When this information was sourced.',
            'note': 'Optional. Notes about this source.',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Order sources by name
        self.fields['source'].queryset = Source.objects.all().order_by('name')
