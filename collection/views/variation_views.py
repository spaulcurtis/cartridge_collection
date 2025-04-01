from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.core.exceptions import ValidationError
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box, VariationSource, Source
from ..forms.variation_forms import VariationForm, VariationSourceForm
from ..utils.note_utils import process_notes

def variation_detail(request, caliber_code, variation_id):
    """View for showing details of a specific variation"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get the variation
    variation = get_object_or_404(Variation, id=variation_id)
    
    # Check if this variation belongs to the right caliber and get parent entities
    if variation.load:
        load = variation.load
        date = None
        headstamp = load.headstamp
        # Verify this belongs to the right caliber
        if headstamp.manufacturer.country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    elif variation.date:
        date = variation.date
        load = date.load
        headstamp = load.headstamp
        # Verify this belongs to the right caliber
        if headstamp.manufacturer.country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    else:
        # This should not happen due to model validation, but just in case
        messages.error(request, "Invalid variation - no parent load or date found.")
        return redirect('dashboard', caliber_code=caliber.code)
    
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Process notes
    variation_notes = process_notes(variation.note)
    variation.note_has_notes = variation_notes['has_notes']
    variation.note_public_notes = variation_notes['public_notes']
    variation.note_confidential_notes = variation_notes['confidential_notes']
    variation.note_has_confidential = variation_notes['has_confidential']
    
    # Get source information
    variation_sources = VariationSource.objects.filter(variation=variation).select_related('source')
    
    # Get ContentType IDs for box queries
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get boxes directly associated with this variation
    direct_boxes = Box.objects.filter(
        content_type=variation_content_type,
        object_id=variation.pk
    ).order_by('bid')
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'country': country,
        'manufacturer': manufacturer,
        'headstamp': headstamp,
        'load': load,
        'date': date,
        'variation': variation,
        'direct_boxes': direct_boxes,
        'variation_content_type': variation_content_type,
        'variation_sources': variation_sources,
    }
    
    return render(request, 'collection/variation_detail.html', context)


def variation_create_for_load(request, caliber_code, load_id):
    """View for creating a new variation for a load"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    load = get_object_or_404(Load, id=load_id, headstamp__manufacturer__country__caliber=caliber)
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    if request.method == 'POST':
        # First create s variation object with proper relationship
        variation = Variation(load=load, date=None)

        form = VariationForm(request.POST, request.FILES, instance=variation)

        if form.is_valid():
            form.save()
            messages.success(request, f"Variation '{variation.cart_id}' was created successfully.")
            return redirect('variation_detail', caliber_code=caliber_code, variation_id=variation.id)

    else:
        form = VariationForm()
    
    return render(request, 'collection/variation_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'load': load,
        'date': None,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Add New Variation to Load {load.cart_id}',
        'submit_text': 'Create Variation',
        'parent_type': 'load',
    })


def variation_create_for_date(request, caliber_code, date_id):
    """View for creating a new variation for a date"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    date = get_object_or_404(Date, id=date_id, load__headstamp__manufacturer__country__caliber=caliber)
    load = date.load
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    if request.method == 'POST':
        # First create s variation object with proper relationship
        variation = Variation(load=None, date=date)

        form = VariationForm(request.POST, request.FILES, instance=variation)

        if form.is_valid():
            form.save()
            messages.success(request, f"Variation '{variation.cart_id}' was created successfully.")
            return redirect('variation_detail', caliber_code=caliber_code, variation_id=variation.id)

    else:
        form = VariationForm()
    
    return render(request, 'collection/variation_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'load': load,
        'date': date,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Add New Variation to Date {date.cart_id}',
        'submit_text': 'Create Variation',
        'parent_type': 'date',
    })


def variation_update(request, caliber_code, variation_id):
    """View for updating a variation"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    variation = get_object_or_404(Variation, id=variation_id)
    
    # Check if this variation belongs to the right caliber and get parent entities
    if variation.load:
        load = variation.load
        date = None
        parent_type = 'load'
        if load.headstamp.manufacturer.country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    elif variation.date:
        date = variation.date
        load = date.load
        parent_type = 'date'
        if load.headstamp.manufacturer.country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    else:
        # This should not happen due to model validation, but just in case
        messages.error(request, "Invalid variation - no parent load or date found.")
        return redirect('dashboard', caliber_code=caliber.code)
    
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Get source information
    variation_sources = VariationSource.objects.filter(variation=variation).select_related('source')
    
    if request.method == 'POST':
        form = VariationForm(request.POST, request.FILES, instance=variation)
        if form.is_valid():
            form.save()
            messages.success(request, f"Variation '{variation.cart_id}' was updated successfully.")
            return redirect('variation_detail', caliber_code=caliber_code, variation_id=variation.id)
    else:
        form = VariationForm(instance=variation)
        
    # Source form for adding new sources
    source_form = VariationSourceForm()
    
    return render(request, 'collection/variation_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'source_form': source_form,
        'variation': variation,
        'load': load,
        'date': date,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Edit Variation: {variation.cart_id}',
        'submit_text': 'Update Variation',
        'variation_sources': variation_sources,
        'parent_type': parent_type,
    })


def variation_delete(request, caliber_code, variation_id):
    """View for deleting a variation"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    variation = get_object_or_404(Variation, id=variation_id)
    
    # Check if this variation belongs to the right caliber and get parent entities
    if variation.load:
        load = variation.load
        date = None
        parent_type = 'load'
        parent_id = load.id
        if load.headstamp.manufacturer.country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    elif variation.date:
        date = variation.date
        load = date.load
        parent_type = 'date'
        parent_id = date.id
        if load.headstamp.manufacturer.country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    else:
        # This should not happen due to model validation, but just in case
        messages.error(request, "Invalid variation - no parent load or date found.")
        return redirect('dashboard', caliber_code=caliber.code)
    
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Check if there are any direct boxes attached
    variation_content_type = ContentType.objects.get_for_model(Variation)
    has_boxes = Box.objects.filter(content_type=variation_content_type, object_id=variation.pk).exists()
    
    # Process notes for display in the template
    processed_notes = process_notes(variation.note)
    
    if request.method == 'POST':
        if has_boxes:
            messages.error(request, f"Cannot delete '{variation.cart_id}' because it has boxes directly associated with it. Remove the boxes first.")
            return redirect('variation_detail', caliber_code=caliber_code, variation_id=variation.id)
            
        variation_cart_id = variation.cart_id
        variation.delete()
        messages.success(request, f"Variation '{variation_cart_id}' was deleted successfully.")
        
        # Redirect to the appropriate parent
        if parent_type == 'load':
            return redirect('load_detail', caliber_code=caliber_code, load_id=parent_id)
        else:  # date
            return redirect('date_detail', caliber_code=caliber_code, date_id=parent_id)
    
    return render(request, 'collection/variation_confirm_delete.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'variation': variation,
        'load': load,
        'date': date,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Delete Variation: {variation.cart_id}',
        'has_boxes': has_boxes,
        'can_delete': not has_boxes,
        'variation_notes': processed_notes,
        'parent_type': parent_type,
    })


def variation_add_source(request, caliber_code, variation_id):
    """View for adding a source to a variation"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    variation = get_object_or_404(Variation, id=variation_id)
    
    # Verify this belongs to the right caliber
    if variation.load and variation.load.headstamp.manufacturer.country.caliber != caliber:
        return redirect('dashboard', caliber_code=caliber.code)
    elif variation.date and variation.date.load.headstamp.manufacturer.country.caliber != caliber:
        return redirect('dashboard', caliber_code=caliber.code)
    
    if request.method == 'POST':
        form = VariationSourceForm(request.POST)
        if form.is_valid():
            source_link = form.save(commit=False)
            source_link.variation = variation
            source_link.save()
            messages.success(request, f"Source '{source_link.source.name}' was added to variation.")
            return redirect('variation_update', caliber_code=caliber_code, variation_id=variation.id)
    
    # If form is invalid, the variation_update view will handle it
    return redirect('variation_update', caliber_code=caliber_code, variation_id=variation.id)


def variation_remove_source(request, caliber_code, variation_id, source_id):
    """View for removing a source from a variation"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    variation = get_object_or_404(Variation, id=variation_id)
    
    # Verify this belongs to the right caliber
    if variation.load and variation.load.headstamp.manufacturer.country.caliber != caliber:
        return redirect('dashboard', caliber_code=caliber.code)
    elif variation.date and variation.date.load.headstamp.manufacturer.country.caliber != caliber:
        return redirect('dashboard', caliber_code=caliber.code)
        
    source_link = get_object_or_404(VariationSource, id=source_id, variation=variation)
    
    if request.method == 'POST':
        source_name = source_link.source.name
        source_link.delete()
        messages.success(request, f"Source '{source_name}' was removed from variation.")
    
    return redirect('variation_update', caliber_code=caliber_code, variation_id=variation.id)