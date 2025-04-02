from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box, BoxSource, Source
from ..forms.box_forms import BoxForm, BoxSourceForm, BoxMoveForm
from ..utils.note_utils import process_notes

def box_detail(request, caliber_code, box_id):
    """View for showing details of a specific box"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get the box
    box = get_object_or_404(Box, id=box_id)
    
    # Verify this belongs to the right caliber
    parent_caliber = box.parent_caliber()
    if parent_caliber != caliber:
        return redirect('dashboard', caliber_code=caliber.code)
    
    # Get parent entity
    parent_obj = box.parent
    
    # Determine the parent type and prepare navigation info
    parent_type = box.content_type.model_class().__name__.lower()
    
    # Prepare navigation hierarchy based on parent type
    if parent_type == 'country':
        country = parent_obj
        manufacturer = None
        headstamp = None
        load = None
        date = None
        variation = None
    elif parent_type == 'manufacturer':
        manufacturer = parent_obj
        country = manufacturer.country
        headstamp = None
        load = None
        date = None
        variation = None
    elif parent_type == 'headstamp':
        headstamp = parent_obj
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        load = None
        date = None
        variation = None
    elif parent_type == 'load':
        load = parent_obj
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        date = None
        variation = None
    elif parent_type == 'date':
        date = parent_obj
        load = date.load
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        variation = None
    elif parent_type == 'variation':
        variation = parent_obj
        if variation.load:
            load = variation.load
            date = None
        else:
            date = variation.date
            load = date.load
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
    else:
        # This should not happen, but just in case
        messages.error(request, "Invalid parent type for box.")
        return redirect('dashboard', caliber_code=caliber.code)
    
    # Process notes
    box_notes = process_notes(box.note)
    box.note_has_notes = box_notes['has_notes']
    box.note_public_notes = box_notes['public_notes']
    box.note_confidential_notes = box_notes['confidential_notes']
    box.note_has_confidential = box_notes['has_confidential']
    
    # Get source information
    box_sources = BoxSource.objects.filter(box=box).select_related('source')
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'box': box,
        'country': country,
        'manufacturer': manufacturer,
        'headstamp': headstamp,
        'load': load,
        'date': date,
        'variation': variation,
        'parent_type': parent_type,
        'parent_obj': parent_obj,
        'box_sources': box_sources,
    }
    
    return render(request, 'collection/box_detail.html', context)


def _create_or_update_box(request, caliber_code, content_type, object_id, instance=None):
    """Helper function for creating or updating boxes"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get the parent model and object
    parent_model = content_type.model_class()
    parent_obj = get_object_or_404(parent_model, id=object_id)
    
    # Verify this belongs to the right caliber
    # Prepare navigation hierarchy based on parent type
    parent_type = parent_model.__name__.lower()
    
    # Prepare navigation hierarchy based on parent type
    if parent_type == 'country':
        country = parent_obj
        manufacturer = None
        headstamp = None
        load = None
        date = None
        variation = None
        # Check if this country belongs to the right caliber
        if country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    elif parent_type == 'manufacturer':
        manufacturer = parent_obj
        country = manufacturer.country
        headstamp = None
        load = None
        date = None
        variation = None
        if country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    elif parent_type == 'headstamp':
        headstamp = parent_obj
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        load = None
        date = None
        variation = None
        if country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    elif parent_type == 'load':
        load = parent_obj
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        date = None
        variation = None
        if country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    elif parent_type == 'date':
        date = parent_obj
        load = date.load
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        variation = None
        if country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    elif parent_type == 'variation':
        variation = parent_obj
        if variation.load:
            load = variation.load
            date = None
        else:
            date = variation.date
            load = date.load
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        if country.caliber != caliber:
            return redirect('dashboard', caliber_code=caliber.code)
    else:
        # This should not happen, but just in case
        messages.error(request, "Invalid parent type for box.")
        return redirect('dashboard', caliber_code=caliber.code)
    
    if request.method == 'POST':
        form = BoxForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            box = form.save(commit=False)
            
            # Set content_type and object_id if creating a new box
            if not instance:
                box.content_type = content_type
                box.object_id = object_id
                
            box.save()
            
            action = "updated" if instance else "created"
            messages.success(request, f"Box '{box.bid}' was {action} successfully.")
            return redirect('box_detail', caliber_code=caliber_code, box_id=box.id)
    else:
        form = BoxForm(instance=instance)
    
    # Get parent display info for the template
    parent_display = None
    if parent_type == 'country':
        parent_display = country.name
    elif parent_type == 'manufacturer':
        parent_display = f"{manufacturer.code}"
        if manufacturer.name:
            parent_display += f" - {manufacturer.name}"
    elif parent_type == 'headstamp':
        parent_display = f"{headstamp.code}"
        if headstamp.name:
            parent_display += f" - {headstamp.name}"
    elif parent_type == 'load':
        parent_display = f"{load.cart_id}"
        if load.description:
            parent_display += f" - {load.description}"
    elif parent_type == 'date':
        year_lot = f"{date.year or ''} {date.lot_month or ''}".strip()
        parent_display = f"{date.cart_id}"
        if year_lot:
            parent_display += f" - {year_lot}"
    elif parent_type == 'variation':
        parent_display = f"{variation.cart_id}"
        if variation.description:
            parent_display += f" - {variation.description}"
    
    # Source form for adding new sources (only for editing)
    source_form = None
    box_sources = None
    if instance:
        source_form = BoxSourceForm()
        box_sources = BoxSource.objects.filter(box=instance).select_related('source')
    
    title = f"Edit Box: {instance.bid}" if instance else f"Add New Box to {parent_display}"
    submit_text = "Update Box" if instance else "Create Box"
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'source_form': source_form,
        'box': instance,
        'country': country,
        'manufacturer': manufacturer,
        'headstamp': headstamp,
        'load': load,
        'date': date,
        'variation': variation,
        'parent_type': parent_type,
        'parent_obj': parent_obj,
        'parent_display': parent_display,
        'title': title,
        'submit_text': submit_text,
        'box_sources': box_sources,
    }
    
    return render(request, 'collection/box_form.html', context)


def box_create(request, caliber_code, model_name, object_id):
    """View for creating a new box for a parent object"""
    # Map model names to actual model classes
    model_map = {
        'country': Country,
        'manufacturer': Manufacturer,
        'headstamp': Headstamp,
        'load': Load,
        'date': Date,
        'variation': Variation,
    }
    
    if model_name not in model_map:
        messages.error(request, f"Invalid parent type: {model_name}")
        return redirect('dashboard', caliber_code=caliber_code)
    
    # Get the ContentType for the parent model
    content_type = ContentType.objects.get_for_model(model_map[model_name])
    
    return _create_or_update_box(request, caliber_code, content_type, object_id)


def box_update(request, caliber_code, box_id):
    """View for updating a box"""
    box = get_object_or_404(Box, id=box_id)
    return _create_or_update_box(request, caliber_code, box.content_type, box.object_id, instance=box)


def box_delete(request, caliber_code, box_id):
    """View for deleting a box"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    box = get_object_or_404(Box, id=box_id)
    
    # Get parent entity
    parent_obj = box.parent
    parent_type = box.content_type.model_class().__name__.lower()
    
    # Verify this belongs to the right caliber
    parent_caliber = box.parent_caliber()
    if parent_caliber != caliber:
        return redirect('dashboard', caliber_code=caliber.code)
    
    # Prepare navigation hierarchy based on parent type
    if parent_type == 'country':
        country = parent_obj
        manufacturer = None
        headstamp = None
        load = None
        date = None
        variation = None
    elif parent_type == 'manufacturer':
        manufacturer = parent_obj
        country = manufacturer.country
        headstamp = None
        load = None
        date = None
        variation = None
    elif parent_type == 'headstamp':
        headstamp = parent_obj
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        load = None
        date = None
        variation = None
    elif parent_type == 'load':
        load = parent_obj
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        date = None
        variation = None
    elif parent_type == 'date':
        date = parent_obj
        load = date.load
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        variation = None
    elif parent_type == 'variation':
        variation = parent_obj
        if variation.load:
            load = variation.load
            date = None
        else:
            date = variation.date
            load = date.load
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
    
    # Process notes for display in the template
    processed_notes = process_notes(box.note)
    
    if request.method == 'POST':
        box_bid = box.bid
        box.delete()
        messages.success(request, f"Box '{box_bid}' was deleted successfully.")
        
        # Redirect to the appropriate parent detail page
        if parent_type == 'country':
            return redirect('country_detail', caliber_code=caliber_code, country_id=country.id)
        elif parent_type == 'manufacturer':
            return redirect('manufacturer_detail', caliber_code=caliber_code, manufacturer_id=manufacturer.id)
        elif parent_type == 'headstamp':
            return redirect('headstamp_detail', caliber_code=caliber_code, headstamp_id=headstamp.id)
        elif parent_type == 'load':
            return redirect('load_detail', caliber_code=caliber_code, load_id=load.id)
        elif parent_type == 'date':
            return redirect('date_detail', caliber_code=caliber_code, date_id=date.id)
        elif parent_type == 'variation':
            return redirect('variation_detail', caliber_code=caliber_code, variation_id=variation.id)
        else:
            return redirect('dashboard', caliber_code=caliber_code)
    
    return render(request, 'collection/box_confirm_delete.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'box': box,
        'country': country,
        'manufacturer': manufacturer,
        'headstamp': headstamp,
        'load': load,
        'date': date,
        'variation': variation,
        'title': f'Delete Box: {box.bid}',
        'box_notes': processed_notes,
        'parent_type': parent_type,
    })


def box_add_source(request, caliber_code, box_id):
    """View for adding a source to a box"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    box = get_object_or_404(Box, id=box_id)
    
    # Verify this belongs to the right caliber
    parent_caliber = box.parent_caliber()
    if parent_caliber != caliber:
        return redirect('dashboard', caliber_code=caliber.code)
    
    if request.method == 'POST':
        form = BoxSourceForm(request.POST)
        if form.is_valid():
            source_link = form.save(commit=False)
            source_link.box = box
            source_link.save()
            messages.success(request, f"Source '{source_link.source.name}' was added to box.")
            return redirect('box_update', caliber_code=caliber_code, box_id=box.id)
    
    # If form is invalid, the box_update view will handle it
    return redirect('box_update', caliber_code=caliber_code, box_id=box.id)


def box_remove_source(request, caliber_code, box_id, source_id):
    """View for removing a source from a box"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    box = get_object_or_404(Box, id=box_id)
    
    # Verify this belongs to the right caliber
    parent_caliber = box.parent_caliber()
    if parent_caliber != caliber:
        return redirect('dashboard', caliber_code=caliber.code)
    
    source_link = get_object_or_404(BoxSource, id=source_id, box=box)
    
    if request.method == 'POST':
        source_name = source_link.source.name
        source_link.delete()
        messages.success(request, f"Source '{source_name}' was removed from box.")
    
    return redirect('box_update', caliber_code=caliber_code, box_id=box.id)


def box_move(request, caliber_code, box_id):
    """View for moving a box to a different parent"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    box = get_object_or_404(Box, id=box_id)
    
    # Verify this belongs to the right caliber
    parent_caliber = box.parent_caliber()
    if parent_caliber != caliber:
        return redirect('dashboard', caliber_code=caliber.code)
    
    # Get current parent entity
    current_parent_obj = box.parent
    current_parent_type = box.content_type.model_class().__name__.lower()
    
    # Prepare navigation hierarchy based on current parent type
    if current_parent_type == 'country':
        country = current_parent_obj
        manufacturer = None
        headstamp = None
        load = None
        date = None
        variation = None
    elif current_parent_type == 'manufacturer':
        manufacturer = current_parent_obj
        country = manufacturer.country
        headstamp = None
        load = None
        date = None
        variation = None
    elif current_parent_type == 'headstamp':
        headstamp = current_parent_obj
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        load = None
        date = None
        variation = None
    elif current_parent_type == 'load':
        load = current_parent_obj
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        date = None
        variation = None
    elif current_parent_type == 'date':
        date = current_parent_obj
        load = date.load
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
        variation = None
    elif current_parent_type == 'variation':
        variation = current_parent_obj
        if variation.load:
            load = variation.load
            date = None
        else:
            date = variation.date
            load = date.load
        headstamp = load.headstamp
        manufacturer = headstamp.manufacturer
        country = manufacturer.country
    else:
        # This should not happen, but just in case
        messages.error(request, "Invalid parent type for box.")
        return redirect('dashboard', caliber_code=caliber.code)
    
    # Get model map for content type lookup
    model_map = {
        'country': Country,
        'manufacturer': Manufacturer,
        'headstamp': Headstamp,
        'load': Load,
        'date': Date,
        'variation': Variation,
    }
    
    if request.method == 'POST':
        form = BoxMoveForm(request.POST, caliber=caliber)
        
        if form.is_valid():
            new_parent_type = form.cleaned_data['parent_type']
            
            # Get the new parent object based on type
            if new_parent_type == 'country':
                new_parent = form.cleaned_data['country']
            elif new_parent_type == 'manufacturer':
                new_parent = form.cleaned_data['manufacturer']
            elif new_parent_type == 'headstamp':
                new_parent = form.cleaned_data['headstamp']
            elif new_parent_type == 'load':
                new_parent = form.cleaned_data['load']
            elif new_parent_type == 'date':
                new_parent = form.cleaned_data['date']
            elif new_parent_type == 'variation':
                new_parent = form.cleaned_data['variation']
            
            # Check if the parent is the same
            if (new_parent_type == current_parent_type and 
                new_parent.id == current_parent_obj.id):
                messages.info(request, f"Box '{box.bid}' is already attached to this {new_parent_type}.")
                return redirect('box_detail', caliber_code=caliber_code, box_id=box.id)
            
            # Update the box's parent
            new_content_type = ContentType.objects.get_for_model(model_map[new_parent_type])
            
            # Get display info for the message
            current_parent_display = box.get_parent_display()
            
            box.content_type = new_content_type
            box.object_id = new_parent.id
            box.save()
            
            # Get the new parent display
            new_parent_display = box.get_parent_display()
            
            messages.success(
                request, 
                f"Box '{box.bid}' was moved from {current_parent_type} '{current_parent_display}' "
                f"to {new_parent_type} '{new_parent_display}'."
            )
            return redirect('box_detail', caliber_code=caliber_code, box_id=box.id)
    else:
        # Create the form with initial values
        form = BoxMoveForm(
            initial={'parent_type': current_parent_type},
            caliber=caliber
        )
    
    # Format current parent display for the template
    current_parent_display = box.get_parent_display()
    
    return render(request, 'collection/box_move_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'box': box,
        'country': country,
        'manufacturer': manufacturer,
        'headstamp': headstamp,
        'load': load,
        'date': date,
        'variation': variation,
        'current_parent_type': current_parent_type,
        'current_parent_obj': current_parent_obj,
        'current_parent_display': current_parent_display,
        'title': f'Move Box: {box.bid}',
        'submit_text': 'Move Box',
    })