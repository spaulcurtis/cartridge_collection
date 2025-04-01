from django import forms
from ..models import Load, Source, LoadSource

class LoadForm(forms.ModelForm):
    """Form for creating and editing loads"""
    
    class Meta:
        model = Load
        fields = ['load_type', 'bullet', 'is_magnetic', 'case_type', 'primer', 'pa_color', 'cc', 'description', 'note', 'image', 'acquisition_note', 'price']
        widgets = {
            'load_type': forms.Select(attrs={'class': 'form-select'}),
            'bullet': forms.Select(attrs={'class': 'form-select'}),
            'is_magnetic': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'case_type': forms.Select(attrs={'class': 'form-select'}),
            'primer': forms.Select(attrs={'class': 'form-select'}),
            'pa_color': forms.Select(attrs={'class': 'form-select'}),
            'cc': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description of this load'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Notes about this load'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'acquisition_note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Acquisition information'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price/value', 'step': '0.01'}),
        }
        labels = {
            'load_type': 'Load Type',
            'bullet': 'Bullet Type',
            'is_magnetic': 'Is Magnetic',
            'case_type': 'Case Type',
            'primer': 'Primer Type',
            'pa_color': 'Primer Annulus Color',
            'cc': 'Credibility Code',
            'description': 'Description',
            'note': 'Notes',
            'image': 'Load Image',
            'acquisition_note': 'Acquisition Note',
            'price': 'Price/Value',
        }
        help_texts = {
            'load_type': 'Required. Type of this load.',
            'bullet': 'Optional. Type of bullet used in this load.',
            'is_magnetic': 'Check if the bullet is magnetic.',
            'case_type': 'Optional. Type of case used in this load.',
            'primer': 'Optional. Type of primer used in this load.',
            'pa_color': 'Optional. Color of the primer annulus.',
            'cc': 'Credibility of this information.',
            'description': 'Optional. Brief description of this load.',
            'note': 'Optional. Additional information about this load. Use double braces &#123;&#123; &#125;&#125; around confidential notes.',
            'image': 'Optional. Upload an image of the load.',
            'acquisition_note': 'Optional. Information about how this item was acquired.',
            'price': 'Optional. Purchase price or estimated value.',
        }


class LoadSourceForm(forms.ModelForm):
    """Form for adding sources to loads"""
    
    class Meta:
        model = LoadSource
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
            'source': 'Select a source for this load information.',
            'date_sourced': 'Optional. When this information was sourced.',
            'note': 'Optional. Notes about this source.',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Order sources by name
        self.fields['source'].queryset = Source.objects.all().order_by('name')
