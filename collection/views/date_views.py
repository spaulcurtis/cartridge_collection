from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box, DateSource, Source
from ..forms.date_forms import DateForm, DateSourceForm
from ..utils.note_utils import process_notes

def date_detail(request, caliber_code, date_id):
    """View for showing details of a specific date"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get the date
    date = get_object_or_404(Date, id=date_id, load__headstamp__manufacturer__country__caliber=caliber)
    
    # Get the load, headstamp, manufacturer and country
    load = date.load
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Process notes
    date_notes = process_notes(date.note)
    date.note_has_notes = date_notes['has_notes']
    date.note_public_notes = date_notes['public_notes']
    date.note_confidential_notes = date_notes['confidential_notes']
    date.note_has_confidential = date_notes['has_confidential']
    
    # Get source information
    date_sources = DateSource.objects.filter(date=date).select_related('source')
    
    # Get ContentType IDs for box queries
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get date variations for this date
    date_variations = Variation.objects.filter(date=date, load__isnull=True).order_by('cart_id')
    
    # Initialize box counts for date variations
    for var in date_variations:
        var.box_count = 0
        var.box_image_count = 0
    
    # Variation-level boxes
    var_box_counts = Box.objects.filter(
        content_type=variation_content_type,
        object_id__in=[v.id for v in date_variations]
    ).values('object_id').annotate(
        box_count=Count('id'),
        image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
    )
    
    for item in var_box_counts:
        var_id = item['object_id']
        box_count = item['box_count']
        image_count = item['image_count']
        
        for var in date_variations:
            if var.id == var_id:
                var.box_count = box_count
                var.box_image_count = image_count
                break
    
    # Get boxes directly associated with this date
    direct_boxes = Box.objects.filter(
        content_type=date_content_type,
        object_id=date.pk
    ).order_by('bid')
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'country': country,
        'manufacturer': manufacturer,
        'headstamp': headstamp,
        'load': load,
        'date': date,
        'date_variations': date_variations,
        'direct_boxes': direct_boxes,
        'date_content_type': date_content_type,
        'date_sources': date_sources,
    }
    
    return render(request, 'collection/date_detail.html', context)


def date_create(request, caliber_code, load_id):
    """View for creating a new date"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    load = get_object_or_404(Load, id=load_id, headstamp__manufacturer__country__caliber=caliber)
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    if request.method == 'POST':
        form = DateForm(request.POST, request.FILES)
        if form.is_valid():
            date = form.save(commit=False)
            date.load = load
            date.save()
            messages.success(request, f"Date '{date.cart_id}' was created successfully.")
            return redirect('date_detail', caliber_code=caliber_code, date_id=date.id)
    else:
        form = DateForm()
    
    return render(request, 'collection/date_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'load': load,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Add New Date to {load.cart_id}',
        'submit_text': 'Create Date',
    })


def date_update(request, caliber_code, date_id):
    """View for updating a date"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    date = get_object_or_404(Date, id=date_id, load__headstamp__manufacturer__country__caliber=caliber)
    load = date.load
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Get source information
    date_sources = DateSource.objects.filter(date=date).select_related('source')
    
    if request.method == 'POST':
        form = DateForm(request.POST, request.FILES, instance=date)
        if form.is_valid():
            form.save()
            messages.success(request, f"Date '{date.cart_id}' was updated successfully.")
            return redirect('date_detail', caliber_code=caliber_code, date_id=date.id)
    else:
        form = DateForm(instance=date)
        
    # Source form for adding new sources
    source_form = DateSourceForm()
    
    return render(request, 'collection/date_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'source_form': source_form,
        'date': date,
        'load': load,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Edit Date: {date.cart_id}',
        'submit_text': 'Update Date',
        'date_sources': date_sources,
    })


def date_delete(request, caliber_code, date_id):
    """View for deleting a date"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    date = get_object_or_404(Date, id=date_id, load__headstamp__manufacturer__country__caliber=caliber)
    load = date.load
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Check if there are any dependent variations
    has_variations = Variation.objects.filter(date=date).exists()
    
    # Check if there are any direct boxes attached
    date_content_type = ContentType.objects.get_for_model(Date)
    has_boxes = Box.objects.filter(content_type=date_content_type, object_id=date.pk).exists()
    
    # Process notes for display in the template
    processed_notes = process_notes(date.note)
    
    if request.method == 'POST':
        if has_variations:
            messages.error(request, f"Cannot delete '{date.cart_id}' because it has variations associated with it. Remove the variations first.")
            return redirect('date_detail', caliber_code=caliber_code, date_id=date.id)
        
        if has_boxes:
            messages.error(request, f"Cannot delete '{date.cart_id}' because it has boxes directly associated with it. Remove the boxes first.")
            return redirect('date_detail', caliber_code=caliber_code, date_id=date.id)
            
        date_cart_id = date.cart_id
        date.delete()
        messages.success(request, f"Date '{date_cart_id}' was deleted successfully.")
        return redirect('load_detail', caliber_code=caliber_code, load_id=load.id)
    
    return render(request, 'collection/date_confirm_delete.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'date': date,
        'load': load,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Delete Date: {date.cart_id}',
        'has_variations': has_variations,
        'has_boxes': has_boxes,
        'can_delete': not (has_variations or has_boxes),
        'date_notes': processed_notes,
    })


def date_add_source(request, caliber_code, date_id):
    """View for adding a source to a date"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    date = get_object_or_404(Date, id=date_id, load__headstamp__manufacturer__country__caliber=caliber)
    
    if request.method == 'POST':
        form = DateSourceForm(request.POST)
        if form.is_valid():
            source_link = form.save(commit=False)
            source_link.date = date
            source_link.save()
            messages.success(request, f"Source '{source_link.source.name}' was added to date.")
            return redirect('date_update', caliber_code=caliber_code, date_id=date.id)
    
    # If form is invalid, the date_update view will handle it
    return redirect('date_update', caliber_code=caliber_code, date_id=date.id)


def date_remove_source(request, caliber_code, date_id, source_id):
    """View for removing a source from a date"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    date = get_object_or_404(Date, id=date_id, load__headstamp__manufacturer__country__caliber=caliber)
    source_link = get_object_or_404(DateSource, id=source_id, date=date)
    
    if request.method == 'POST':
        source_name = source_link.source.name
        source_link.delete()
        messages.success(request, f"Source '{source_name}' was removed from date.")
    
    return redirect('date_update', caliber_code=caliber_code, date_id=date.id)
