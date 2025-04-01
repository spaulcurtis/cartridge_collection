from django import forms
from ..models import Variation, Source, VariationSource

class VariationForm(forms.ModelForm):
    """Form for creating and editing variations"""
    
    class Meta:
        model = Variation
        fields = ['cc', 'description', 'note', 'image', 'acquisition_note', 'price']
        widgets = {
            'cc': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description of this variation'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Notes about this variation'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'acquisition_note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Acquisition information'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price/value', 'step': '0.01'}),
        }
        labels = {
            'cc': 'Credibility Code',
            'description': 'Description',
            'note': 'Notes',
            'image': 'Variation Image',
            'acquisition_note': 'Acquisition Note',
            'price': 'Price/Value',
        }
        help_texts = {
            'cc': 'Credibility of this information.',
            'description': 'Description of this variation (what makes it different from the standard load/date).',
            'note': 'Optional. Additional information about this variation. Use double braces &#123;&#123; &#125;&#125; around confidential notes.',
            'image': 'Optional. Upload an image of the variation.',
            'acquisition_note': 'Optional. Information about how this item was acquired.',
            'price': 'Optional. Purchase price or estimated value.',
        }

class VariationSourceForm(forms.ModelForm):
    """Form for adding sources to variations"""
    
    class Meta:
        model = VariationSource
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
            'source': 'Select a source for this variation information.',
            'date_sourced': 'Optional. When this information was sourced.',
            'note': 'Optional. Notes about this source.',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Order sources by name
        self.fields['source'].queryset = Source.objects.all().order_by('name')
