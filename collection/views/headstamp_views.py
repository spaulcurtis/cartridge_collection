from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box, HeadstampSource, Source
from ..forms.headstamp_forms import HeadstampForm, HeadstampSourceForm, HeadstampMoveForm
from ..utils.note_utils import process_notes

def headstamp_detail(request, caliber_code, headstamp_id):
    """View for showing details of a specific headstamp"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get the headstamp
    headstamp = get_object_or_404(Headstamp, id=headstamp_id, manufacturer__country__caliber=caliber)
    
    # Get the manufacturer and country
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Process notes
    from ..utils.note_utils import process_notes
    headstamp_notes = process_notes(headstamp.note)
    headstamp.note_has_notes = headstamp_notes['has_notes']
    headstamp.note_public_notes = headstamp_notes['public_notes']
    headstamp.note_confidential_notes = headstamp_notes['confidential_notes']
    headstamp.note_has_confidential = headstamp_notes['has_confidential']
    
    # Get source information
    headstamp_sources = HeadstampSource.objects.filter(headstamp=headstamp).select_related('source')
    
    # Check if case manufacturer is different from primary manufacturer
    show_case_manufacturer = (
    headstamp.primary_manufacturer and 
    headstamp.primary_manufacturer.id and 
    headstamp.primary_manufacturer != manufacturer
    )
    
    # Find other manufacturers with the same headstamp code
    other_manufacturers = Manufacturer.objects.filter(
        headstamps__code=headstamp.code,
        id__isnull=False  # Ensure id is not null
    ).exclude(
        id=manufacturer.id
    ).select_related('country').order_by('country__short_name', 'code')

    # Get ContentType IDs for box queries
    headstamp_content_type = ContentType.objects.get_for_model(Headstamp)
    load_content_type = ContentType.objects.get_for_model(Load)
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get loads for this headstamp
    loads = Load.objects.filter(headstamp=headstamp).order_by('cart_id')
    
    # Create a mapping of load_id to load objects for easy reference
    load_dict = {load.id: load for load in loads}
    
    # For each load, gather the related IDs at various levels
    load_related_ids = {}
    
    # Date IDs per load
    date_query = Date.objects.filter(
        load__in=loads
    ).values('load_id', 'id', 'image')
    
    for item in date_query:
        load_id = item['load_id']
        date_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if load_id not in load_related_ids:
            load_related_ids[load_id] = {
                'date_ids': [],
                'load_var_ids': [],
                'date_var_ids': []
            }
            
        load_related_ids[load_id]['date_ids'].append(date_id)
        
        # Count dates
        if not hasattr(load_dict[load_id], 'date_count'):
            load_dict[load_id].date_count = 0
            load_dict[load_id].date_image_count = 0
            
        load_dict[load_id].date_count += 1
        if has_image:
            load_dict[load_id].date_image_count += 1
    
    # Load Variation IDs per load
    load_var_query = Variation.objects.filter(
        load__in=loads,
        load__isnull=False
    ).values('load_id', 'id', 'image')
    
    for item in load_var_query:
        load_id = item['load_id']
        var_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if load_id not in load_related_ids:
            load_related_ids[load_id] = {
                'date_ids': [],
                'load_var_ids': [],
                'date_var_ids': []
            }
            
        load_related_ids[load_id]['load_var_ids'].append(var_id)
        
        # Count load variations
        if not hasattr(load_dict[load_id], 'var_count'):
            load_dict[load_id].var_count = 0
            load_dict[load_id].var_image_count = 0
            
        load_dict[load_id].var_count += 1
        if has_image:
            load_dict[load_id].var_image_count += 1
    
    # Date Variation IDs per load
    date_var_query = Variation.objects.filter(
        date__load__in=loads,
        date__isnull=False
    ).values('date__load_id', 'id', 'image')
    
    for item in date_var_query:
        load_id = item['date__load_id']
        var_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if load_id not in load_related_ids:
            continue
            
        load_related_ids[load_id]['date_var_ids'].append(var_id)
        
        # Count date variations
        if not hasattr(load_dict[load_id], 'date_var_count'):
            load_dict[load_id].date_var_count = 0
            load_dict[load_id].date_var_image_count = 0
            
        load_dict[load_id].date_var_count += 1
        if has_image:
            load_dict[load_id].date_var_image_count += 1
    
    # Initialize box counts for loads
    for load in loads:
        load.box_count = 0
        load.box_image_count = 0
    
    # Load-level boxes
    load_box_counts = Box.objects.filter(
        content_type=load_content_type,
        object_id__in=[l.id for l in loads]
    ).values('object_id').annotate(
        box_count=Count('id'),
        image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
    )
    
    for item in load_box_counts:
        load_id = item['object_id']
        box_count = item['box_count']
        image_count = item['image_count']
        
        if load_id in load_dict:
            load_dict[load_id].box_count += box_count
            load_dict[load_id].box_image_count += image_count
    
    # Date-level boxes
    for load_id, ids in load_related_ids.items():
        date_ids = ids.get('date_ids', [])
        if not date_ids:
            continue
            
        date_box_counts = Box.objects.filter(
            content_type=date_content_type,
            object_id__in=date_ids
        ).aggregate(
            box_count=Count('id'),
            image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
        )
        
        load_dict[load_id].box_count += date_box_counts['box_count'] or 0
        load_dict[load_id].box_image_count += date_box_counts['image_count'] or 0
    
    # Load Variation-level boxes
    for load_id, ids in load_related_ids.items():
        load_var_ids = ids.get('load_var_ids', [])
        if not load_var_ids:
            continue
            
        load_var_box_counts = Box.objects.filter(
            content_type=variation_content_type,
            object_id__in=load_var_ids
        ).aggregate(
            box_count=Count('id'),
            image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
        )
        
        load_dict[load_id].box_count += load_var_box_counts['box_count'] or 0
        load_dict[load_id].box_image_count += load_var_box_counts['image_count'] or 0
    
    # Date Variation-level boxes
    for load_id, ids in load_related_ids.items():
        date_var_ids = ids.get('date_var_ids', [])
        if not date_var_ids:
            continue
            
        date_var_box_counts = Box.objects.filter(
            content_type=variation_content_type,
            object_id__in=date_var_ids
        ).aggregate(
            box_count=Count('id'),
            image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
        )
        
        load_dict[load_id].box_count += date_var_box_counts['box_count'] or 0
        load_dict[load_id].box_image_count += date_var_box_counts['image_count'] or 0
    
    # Initialize counts for loads without data
    for load in loads:
        if not hasattr(load, 'date_count'):
            load.date_count = 0
            load.date_image_count = 0
        if not hasattr(load, 'var_count'):
            load.var_count = 0
            load.var_image_count = 0
        if not hasattr(load, 'date_var_count'):
            load.date_var_count = 0
            load.date_var_image_count = 0
    
    # Get boxes directly associated with this headstamp
    direct_boxes = Box.objects.filter(
        content_type=headstamp_content_type,
        object_id=headstamp.pk
    ).order_by('bid')
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'country': country,
        'manufacturer': manufacturer,
        'headstamp': headstamp,
        'loads': loads,
        'direct_boxes': direct_boxes,
        'headstamp_content_type': headstamp_content_type,
        'other_manufacturers': other_manufacturers,
        'headstamp_sources': headstamp_sources,
        'show_case_manufacturer': show_case_manufacturer,
    }
    
    return render(request, 'collection/headstamp_detail.html', context)


def headstamp_create(request, caliber_code, manufacturer_id):
    """View for creating a new headstamp"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id, country__caliber=caliber)
    country = manufacturer.country
    
    if request.method == 'POST':
        form = HeadstampForm(manufacturer, request.POST, request.FILES)
        if form.is_valid():
            headstamp = form.save(commit=False)
            headstamp.manufacturer = manufacturer
            
            # Check for uniqueness constraint violation
            if Headstamp.objects.filter(manufacturer=manufacturer, code=headstamp.code).exists():
                messages.error(
                    request, 
                    f"Cannot create headstamp with code '{headstamp.code}' because a headstamp with "
                    f"this code already exists for manufacturer {manufacturer.code}."
                )
                return render(request, 'collection/headstamp_form.html', {
                    'caliber': caliber,
                    'all_calibers': all_calibers,
                    'form': form,
                    'manufacturer': manufacturer,
                    'country': country,
                    'title': f'Add New Headstamp to {manufacturer.code}',
                    'submit_text': 'Create Headstamp',
                })
            
            headstamp.save()
            messages.success(request, f"Headstamp '{headstamp.code}' was created successfully.")
            return redirect('headstamp_detail', caliber_code=caliber_code, headstamp_id=headstamp.id)
    else:
        form = HeadstampForm(manufacturer)
    
    return render(request, 'collection/headstamp_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Add New Headstamp to {manufacturer.code}',
        'submit_text': 'Create Headstamp',
    })

def headstamp_update(request, caliber_code, headstamp_id):
    """View for updating a headstamp"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    headstamp = get_object_or_404(Headstamp, id=headstamp_id, manufacturer__country__caliber=caliber)
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Get source information
    headstamp_sources = HeadstampSource.objects.filter(headstamp=headstamp).select_related('source')
    
    if request.method == 'POST':
        form = HeadstampForm(manufacturer, request.POST, request.FILES, instance=headstamp)
        if form.is_valid():
            updated_headstamp = form.save(commit=False)
            
            # Check for uniqueness constraint violation, but exclude the current headstamp
            if Headstamp.objects.filter(
                manufacturer=manufacturer, 
                code=updated_headstamp.code
            ).exclude(id=headstamp.id).exists():
                messages.error(
                    request, 
                    f"Cannot update headstamp with code '{updated_headstamp.code}' because a headstamp with "
                    f"this code already exists for manufacturer {manufacturer.code}."
                )
                return render(request, 'collection/headstamp_form.html', {
                    'caliber': caliber,
                    'all_calibers': all_calibers,
                    'form': form,
                    'source_form': HeadstampSourceForm(),
                    'headstamp': headstamp,
                    'manufacturer': manufacturer,
                    'country': country,
                    'title': f'Edit Headstamp: {headstamp.code}',
                    'submit_text': 'Update Headstamp',
                    'headstamp_sources': headstamp_sources,
                })
            
            updated_headstamp.save()
            messages.success(request, f"Headstamp '{updated_headstamp.code}' was updated successfully.")
            return redirect('headstamp_detail', caliber_code=caliber_code, headstamp_id=headstamp.id)
    else:
        form = HeadstampForm(manufacturer, instance=headstamp)
        
    # Source form for adding new sources
    source_form = HeadstampSourceForm()
    
    return render(request, 'collection/headstamp_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'source_form': source_form,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Edit Headstamp: {headstamp.code}',
        'submit_text': 'Update Headstamp',
        'headstamp_sources': headstamp_sources,
    })


def headstamp_delete(request, caliber_code, headstamp_id):
    """View for deleting a headstamp"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    headstamp = get_object_or_404(Headstamp, id=headstamp_id, manufacturer__country__caliber=caliber)
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Check if there are any dependent loads
    has_loads = Load.objects.filter(headstamp=headstamp).exists()
    
    # Check if there are any direct boxes attached
    headstamp_content_type = ContentType.objects.get_for_model(Headstamp)
    has_boxes = Box.objects.filter(content_type=headstamp_content_type, object_id=headstamp.pk).exists()
    
    # Process notes for display in the template
    processed_notes = process_notes(headstamp.note)
    
    if request.method == 'POST':
        if has_loads:
            messages.error(request, f"Cannot delete '{headstamp.code}' because it has loads associated with it. Remove the loads first.")
            return redirect('headstamp_detail', caliber_code=caliber_code, headstamp_id=headstamp.id)
        
        if has_boxes:
            messages.error(request, f"Cannot delete '{headstamp.code}' because it has boxes directly associated with it. Remove the boxes first.")
            return redirect('headstamp_detail', caliber_code=caliber_code, headstamp_id=headstamp.id)
            
        headstamp_code = headstamp.code
        headstamp.delete()
        messages.success(request, f"Headstamp '{headstamp_code}' was deleted successfully.")
        return redirect('manufacturer_detail', caliber_code=caliber_code, manufacturer_id=manufacturer.id)
    
    return render(request, 'collection/headstamp_confirm_delete.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Delete Headstamp: {headstamp.code}',
        'has_loads': has_loads,
        'has_boxes': has_boxes,
        'can_delete': not (has_loads or has_boxes),
        'headstamp_notes': processed_notes,
    })


def headstamp_add_source(request, caliber_code, headstamp_id):
    """View for adding a source to a headstamp"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    headstamp = get_object_or_404(Headstamp, id=headstamp_id, manufacturer__country__caliber=caliber)
    
    if request.method == 'POST':
        form = HeadstampSourceForm(request.POST)
        if form.is_valid():
            source_link = form.save(commit=False)
            source_link.headstamp = headstamp
            source_link.save()
            messages.success(request, f"Source '{source_link.source.name}' was added to headstamp.")
            return redirect('headstamp_update', caliber_code=caliber_code, headstamp_id=headstamp.id)
    
    # If form is invalid, the headstamp_update view will handle it
    return redirect('headstamp_update', caliber_code=caliber_code, headstamp_id=headstamp.id)


def headstamp_remove_source(request, caliber_code, headstamp_id, source_id):
    """View for removing a source from a headstamp"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    headstamp = get_object_or_404(Headstamp, id=headstamp_id, manufacturer__country__caliber=caliber)
    source_link = get_object_or_404(HeadstampSource, id=source_id, headstamp=headstamp)
    
    if request.method == 'POST':
        source_name = source_link.source.name
        source_link.delete()
        messages.success(request, f"Source '{source_name}' was removed from headstamp.")
    
    return redirect('headstamp_update', caliber_code=caliber_code, headstamp_id=headstamp.id)

def headstamp_move(request, caliber_code, headstamp_id):
    """View for moving a headstamp to a different manufacturer"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    headstamp = get_object_or_404(Headstamp, id=headstamp_id, manufacturer__country__caliber=caliber)
    current_manufacturer = headstamp.manufacturer
    country = current_manufacturer.country
    
    if request.method == 'POST':
        form = HeadstampMoveForm(request.POST, caliber=caliber)
        if form.is_valid():
            new_manufacturer = form.cleaned_data['new_manufacturer']
            
            # Don't do anything if the manufacturer hasn't changed
            if new_manufacturer == current_manufacturer:
                messages.info(request, f"'{headstamp.code}' is already assigned to {current_manufacturer.code}.")
                return redirect('headstamp_detail', caliber_code=caliber_code, headstamp_id=headstamp.id)
            
            # Check for uniqueness constraint violation
            if Headstamp.objects.filter(manufacturer=new_manufacturer, code=headstamp.code).exists():
                # There's already a headstamp with the same code in the target manufacturer
                messages.error(
                    request, 
                    f"Cannot move '{headstamp.code}' to {new_manufacturer.code} because a headstamp with "
                    f"this code already exists there."
                )
                return render(request, 'collection/headstamp_move_form.html', {
                    'caliber': caliber,
                    'all_calibers': all_calibers,
                    'form': form,
                    'headstamp': headstamp,
                    'current_manufacturer': current_manufacturer,
                    'country': country,
                    'title': f'Move Headstamp: {headstamp.code}',
                    'submit_text': 'Move Headstamp',
                })
            
            # Update the headstamp's manufacturer
            old_manufacturer_code = current_manufacturer.code
            headstamp.manufacturer = new_manufacturer
            headstamp.save()
            
            messages.success(
                request, 
                f"Headstamp '{headstamp.code}' was moved from {old_manufacturer_code} to {new_manufacturer.code}."
            )
            return redirect('headstamp_detail', caliber_code=caliber_code, headstamp_id=headstamp.id)
    else:
        form = HeadstampMoveForm(caliber=caliber)
        
        # Customize the manufacturer display to show country and name
        from django.forms.models import ModelChoiceIterator
        from django.utils.html import format_html
        
        class CustomModelChoiceIterator(ModelChoiceIterator):
            def choice(self, obj):
                return (obj.id, f"{obj.country.name} - {obj.code}{' - ' + obj.name[:30] if obj.name else ''}")
        
        form.fields['new_manufacturer'].widget.choices = CustomModelChoiceIterator(form.fields['new_manufacturer'])
    
    return render(request, 'collection/headstamp_move_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'headstamp': headstamp,
        'current_manufacturer': current_manufacturer,
        'country': country,
        'title': f'Move Headstamp: {headstamp.code}',
        'submit_text': 'Move Headstamp',
    })