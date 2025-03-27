from django import forms

class DatabaseExamineForm(forms.Form):
    """Form for uploading a SQLite database file for examination"""
    database_file = forms.FileField(
        label='SQLite Database File',
        help_text='Select the SQLite database file from the old application.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

class DatabaseImportForm(forms.Form):
    """Form for configuring how to import from the examined database"""
    selected_tables = forms.MultipleChoiceField(
        label='Tables to Import',
        choices=[],  # Will be populated dynamically
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    IMPORT_MODE_CHOICES = [
        ('merge', 'Merge - Add new records, update existing ones'),
        ('replace', 'Replace - Clear existing records before import')
    ]
    
    import_mode = forms.ChoiceField(
        label='Import Mode',
        choices=IMPORT_MODE_CHOICES,
        initial='merge',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    import_images = forms.BooleanField(
        label='Import Images',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    dry_run = forms.BooleanField(
        label='Dry Run Mode',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, tables=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if tables:
            # Filter out Django system tables and create choices
            self.fields['selected_tables'].choices = [
                (table['name'], f"{table['name']} ({table['count']} rows)")
                for table in tables if not table.get('django_table')
            ]