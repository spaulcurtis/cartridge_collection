from django import forms
from ..models import Date, Source, DateSource

class DateForm(forms.ModelForm):
    """Form for creating and editing dates"""
    
    class Meta:
        model = Date
        fields = ['year', 'lot_month', 'cc', 'description', 'note', 'image', 'acquisition_note', 'price']
        widgets = {
            'year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Year of production'}),
            'lot_month': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lot number or month'}),
            'cc': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description of this date/lot'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Notes about this date/lot'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'acquisition_note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Acquisition information'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price/value', 'step': '0.01'}),
        }
        labels = {
            'year': 'Year',
            'lot_month': 'Lot/Month',
            'cc': 'Credibility Code',
            'description': 'Description',
            'note': 'Notes',
            'image': 'Date/Lot Image',
            'acquisition_note': 'Acquisition Note',
            'price': 'Price/Value',
        }
        help_texts = {
            'year': 'Optional. Year of production.',
            'lot_month': 'Optional. Lot number or month of production.',
            'cc': 'Credibility of this information.',
            'description': 'Optional. Brief description of this date/lot.',
            'note': 'Optional. Additional information about this date/lot. Use double braces &#123;&#123; &#125;&#125; around confidential notes.',
            'image': 'Optional. Upload an image of the date/lot.',
            'acquisition_note': 'Optional. Information about how this item was acquired.',
            'price': 'Optional. Purchase price or estimated value.',
        }

class DateSourceForm(forms.ModelForm):
    """Form for adding sources to dates"""
    
    class Meta:
        model = DateSource
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
            'source': 'Select a source for this date information.',
            'date_sourced': 'Optional. When this information was sourced.',
            'note': 'Optional. Notes about this source.',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Order sources by name
        self.fields['source'].queryset = Source.objects.all().order_by('name')
