from django import forms
from django.contrib.contenttypes.models import ContentType
from ..models import Box, Source, BoxSource, Country, Manufacturer, Headstamp, Load, Date, Variation

class BoxForm(forms.ModelForm):
    """Form for creating and editing boxes"""
    
    class Meta:
        model = Box
        fields = ['cc', 'description', 'note', 'location', 'art_type', 'art_type_other', 'image', 'acquisition_note', 'price']
        widgets = {
            'cc': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description of this box'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Notes about this box'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Physical location in collection'}),
            'art_type': forms.Select(attrs={'class': 'form-select'}),
            'art_type_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specify if Other is selected'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'acquisition_note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Acquisition information'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price/value', 'step': '0.01'}),
        }
        labels = {
            'cc': 'Credibility Code',
            'description': 'Description',
            'note': 'Notes',
            'location': 'Physical Location',
            'art_type': 'Artifact Type',
            'art_type_other': 'Other Artifact Type',
            'image': 'Box Image',
            'acquisition_note': 'Acquisition Note',
            'price': 'Price/Value',
        }
        help_texts = {
            'cc': 'Credibility of this information.',
            'description': 'Description of this box.',
            'note': 'Optional. Additional information about this box. Use double braces &#123;&#123; &#125;&#125; around confidential notes.',
            'location': 'Optional. Physical location of this box in the collection.',
            'art_type': 'Type of artifact.',
            'art_type_other': 'Specify if "Other" is selected for artifact type.',
            'image': 'Optional. Upload an image of the box.',
            'acquisition_note': 'Optional. Information about how this item was acquired.',
            'price': 'Optional. Purchase price or estimated value.',
        }

    def __init__(self, *args, **kwargs):
        # Extract content_type and object_id if provided
        self.content_type = kwargs.pop('content_type', None)
        self.object_id = kwargs.pop('object_id', None)
        
        super().__init__(*args, **kwargs)
        
        # Show or hide art_type_other field based on art_type selection
        if 'art_type' in self.initial and self.initial['art_type'] != 'other':
            self.fields['art_type_other'].widget = forms.HiddenInput()

class BoxSourceForm(forms.ModelForm):
    """Form for adding sources to boxes"""
    
    class Meta:
        model = BoxSource
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
            'source': 'Select a source for this box information.',
            'date_sourced': 'Optional. When this information was sourced.',
            'note': 'Optional. Notes about this source.',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Order sources by name
        self.fields['source'].queryset = Source.objects.all().order_by('name')
