from django import forms
from django.db.models import Q
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


class BoxMoveForm(forms.Form):
    parent_type = forms.ChoiceField(
        choices=[
            ('country', 'Country'),
            ('manufacturer', 'Manufacturer'),
            ('headstamp', 'Headstamp'),
            ('load', 'Load'),
            ('date', 'Date'),
            ('variation', 'Variation'),
        ],
        label="New Parent Type",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'parent-type-select'})
    )
    
    # Country and Manufacturer use dropdowns
    country = forms.ModelChoiceField(
        queryset=Country.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    manufacturer = forms.ModelChoiceField(
        queryset=Manufacturer.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # For Headstamp, use manufacturer dropdown and text input for code
    headstamp_manufacturer = forms.ModelChoiceField(
        queryset=Manufacturer.objects.none(),
        required=False,
        label="Manufacturer",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    headstamp_code = forms.CharField(
        max_length=100, 
        required=False,
        label="Headstamp Code",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    # For Load, Date, and Variation, use text input for cart_id
    load_cart_id = forms.CharField(
        max_length=20, 
        required=False,
        label="Load ID",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    date_cart_id = forms.CharField(
        max_length=20, 
        required=False,
        label="Date ID",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    variation_cart_id = forms.CharField(
        max_length=20, 
        required=False,
        label="Variation ID",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, caliber=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if caliber:
            # Update querysets to filter by caliber
            self.fields['country'].queryset = Country.objects.filter(
                caliber=caliber
            ).order_by('name')
            
            self.fields['manufacturer'].queryset = Manufacturer.objects.filter(
                country__caliber=caliber
            ).order_by('country__name', 'code')
            
            self.fields['headstamp_manufacturer'].queryset = Manufacturer.objects.filter(
                country__caliber=caliber
            ).order_by('country__name', 'code')
            
            # Customize the display for manufacturer fields
            self.fields['country'].label_from_instance = lambda obj: f"{obj.name}"
            
            manufacturer_label = lambda obj: f"{obj.country.name} - {obj.code}{' - ' + obj.name[:30] if obj.name else ''}"
            self.fields['manufacturer'].label_from_instance = manufacturer_label
            self.fields['headstamp_manufacturer'].label_from_instance = manufacturer_label
    
    def clean(self):
        cleaned_data = super().clean()
        parent_type = cleaned_data.get('parent_type')
        
        if parent_type == 'country':
            if not cleaned_data.get('country'):
                self.add_error('country', "Please select a country.")
        
        elif parent_type == 'manufacturer':
            if not cleaned_data.get('manufacturer'):
                self.add_error('manufacturer', "Please select a manufacturer.")
        
        elif parent_type == 'headstamp':
            manufacturer = cleaned_data.get('headstamp_manufacturer')
            code = cleaned_data.get('headstamp_code')
            
            if not manufacturer:
                self.add_error('headstamp_manufacturer', "Please select a manufacturer.")
            
            if not code:
                self.add_error('headstamp_code', "Please enter a headstamp code.")
            
            if manufacturer and code:
                try:
                    headstamp = Headstamp.objects.get(
                        manufacturer=manufacturer,
                        code=code
                    )
                    cleaned_data['headstamp'] = headstamp
                except Headstamp.DoesNotExist:
                    self.add_error('headstamp_code', 
                        f"Headstamp with code '{code}' does not exist for manufacturer {manufacturer.code}.")
        
        elif parent_type == 'load':
            load_cart_id = cleaned_data.get('load_cart_id')
            if not load_cart_id:
                self.add_error('load_cart_id', "Please enter a load ID.")
            else:
                try:
                    load = Load.objects.get(cart_id=load_cart_id)
                    cleaned_data['load'] = load
                except Load.DoesNotExist:
                    self.add_error('load_cart_id', f"Load with ID '{load_cart_id}' does not exist.")
        
        elif parent_type == 'date':
            date_cart_id = cleaned_data.get('date_cart_id')
            if not date_cart_id:
                self.add_error('date_cart_id', "Please enter a date ID.")
            else:
                try:
                    date = Date.objects.get(cart_id=date_cart_id)
                    cleaned_data['date'] = date
                except Date.DoesNotExist:
                    self.add_error('date_cart_id', f"Date with ID '{date_cart_id}' does not exist.")
        
        elif parent_type == 'variation':
            variation_cart_id = cleaned_data.get('variation_cart_id')
            if not variation_cart_id:
                self.add_error('variation_cart_id', "Please enter a variation ID.")
            else:
                try:
                    variation = Variation.objects.get(cart_id=variation_cart_id)
                    cleaned_data['variation'] = variation
                except Variation.DoesNotExist:
                    self.add_error('variation_cart_id', f"Variation with ID '{variation_cart_id}' does not exist.")
        
        return cleaned_data