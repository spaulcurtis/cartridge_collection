# manufacturer_views.py (new file) or add to existing views file

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box
from ..forms.manufacturer_forms import ManufacturerForm, ManufacturerMoveForm
from ..utils.note_utils import process_notes


def manufacturer_detail(request, caliber_code, manufacturer_id):
    """View for showing details of a specific manufacturer"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get the manufacturer
    manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id, country__caliber=caliber)
    
    # Get the country (for breadcrumbs)
    country = manufacturer.country
    
    # Process notes
    from ..utils.note_utils import process_notes
    manufacturer_notes = process_notes(manufacturer.note)
    manufacturer.note_has_notes = manufacturer_notes['has_notes']
    manufacturer.note_public_notes = manufacturer_notes['public_notes']
    manufacturer.note_confidential_notes = manufacturer_notes['confidential_notes']
    manufacturer.note_has_confidential = manufacturer_notes['has_confidential']
    
    # Get ContentType IDs for box queries
    from django.contrib.contenttypes.models import ContentType
    manufacturer_content_type = ContentType.objects.get_for_model(Manufacturer)
    headstamp_content_type = ContentType.objects.get_for_model(Headstamp)
    load_content_type = ContentType.objects.get_for_model(Load)
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get headstamps for this manufacturer
    headstamps = Headstamp.objects.filter(manufacturer=manufacturer).order_by('code')
    
    # Create a mapping of headstamp_id to headstamp objects for easy reference
    headstamp_dict = {headstamp.id: headstamp for headstamp in headstamps}
    
    # For each headstamp, gather the related IDs at various levels
    headstamp_related_ids = {}
    
    # Load IDs per headstamp
    load_query = Load.objects.filter(
        headstamp__in=headstamps
    ).values('headstamp_id', 'id', 'image')
    
    for item in load_query:
        headstamp_id = item['headstamp_id']
        load_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if headstamp_id not in headstamp_related_ids:
            headstamp_related_ids[headstamp_id] = {
                'load_ids': [],
                'date_ids': [],
                'load_var_ids': [],
                'date_var_ids': []
            }
            
        headstamp_related_ids[headstamp_id]['load_ids'].append(load_id)
        
        # Count loads
        if not hasattr(headstamp_dict[headstamp_id], 'load_count'):
            headstamp_dict[headstamp_id].load_count = 0
            headstamp_dict[headstamp_id].load_image_count = 0
            
        headstamp_dict[headstamp_id].load_count += 1
        if has_image:
            headstamp_dict[headstamp_id].load_image_count += 1
    
    # Date IDs per headstamp
    date_query = Date.objects.filter(
        load__headstamp__in=headstamps
    ).values('load__headstamp_id', 'id', 'image')
    
    for item in date_query:
        headstamp_id = item['load__headstamp_id']
        date_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if headstamp_id not in headstamp_related_ids:
            continue
            
        headstamp_related_ids[headstamp_id]['date_ids'].append(date_id)
        
        # Count dates
        if not hasattr(headstamp_dict[headstamp_id], 'date_count'):
            headstamp_dict[headstamp_id].date_count = 0
            headstamp_dict[headstamp_id].date_image_count = 0
            
        headstamp_dict[headstamp_id].date_count += 1
        if has_image:
            headstamp_dict[headstamp_id].date_image_count += 1
    
    # Load Variation IDs per headstamp
    load_var_query = Variation.objects.filter(
        load__headstamp__in=headstamps,
        load__isnull=False
    ).values('load__headstamp_id', 'id', 'image')
    
    for item in load_var_query:
        headstamp_id = item['load__headstamp_id']
        var_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if headstamp_id not in headstamp_related_ids:
            continue
            
        headstamp_related_ids[headstamp_id]['load_var_ids'].append(var_id)
        
        # Count load variations
        if not hasattr(headstamp_dict[headstamp_id], 'var_count'):
            headstamp_dict[headstamp_id].var_count = 0
            headstamp_dict[headstamp_id].var_image_count = 0
            
        headstamp_dict[headstamp_id].var_count += 1
        if has_image:
            headstamp_dict[headstamp_id].var_image_count += 1
    
    # Date Variation IDs per headstamp
    date_var_query = Variation.objects.filter(
        date__load__headstamp__in=headstamps,
        date__isnull=False
    ).values('date__load__headstamp_id', 'id', 'image')
    
    for item in date_var_query:
        headstamp_id = item['date__load__headstamp_id']
        var_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if headstamp_id not in headstamp_related_ids:
            continue
            
        headstamp_related_ids[headstamp_id]['date_var_ids'].append(var_id)
        
        # Count date variations
        if not hasattr(headstamp_dict[headstamp_id], 'date_var_count'):
            headstamp_dict[headstamp_id].date_var_count = 0
            headstamp_dict[headstamp_id].date_var_image_count = 0
            
        headstamp_dict[headstamp_id].date_var_count += 1
        if has_image:
            headstamp_dict[headstamp_id].date_var_image_count += 1
    
    # Initialize box counts for headstamps
    for headstamp in headstamps:
        headstamp.box_count = 0
        headstamp.box_image_count = 0
    
    # Headstamp-level boxes
    headstamp_box_counts = Box.objects.filter(
        content_type=headstamp_content_type,
        object_id__in=[h.id for h in headstamps]
    ).values('object_id').annotate(
        box_count=Count('id'),
        image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
    )
    
    for item in headstamp_box_counts:
        headstamp_id = item['object_id']
        box_count = item['box_count']
        image_count = item['image_count']
        
        if headstamp_id in headstamp_dict:
            headstamp_dict[headstamp_id].box_count += box_count
            headstamp_dict[headstamp_id].box_image_count += image_count
    
    # Load-level boxes
    for headstamp_id, ids in headstamp_related_ids.items():
        load_ids = ids.get('load_ids', [])
        if not load_ids:
            continue
            
        load_box_counts = Box.objects.filter(
            content_type=load_content_type,
            object_id__in=load_ids
        ).aggregate(
            box_count=Count('id'),
            image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
        )
        
        headstamp_dict[headstamp_id].box_count += load_box_counts['box_count'] or 0
        headstamp_dict[headstamp_id].box_image_count += load_box_counts['image_count'] or 0
    
    # Date-level boxes
    for headstamp_id, ids in headstamp_related_ids.items():
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
        
        headstamp_dict[headstamp_id].box_count += date_box_counts['box_count'] or 0
        headstamp_dict[headstamp_id].box_image_count += date_box_counts['image_count'] or 0
    
    # Load Variation-level boxes
    for headstamp_id, ids in headstamp_related_ids.items():
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
        
        headstamp_dict[headstamp_id].box_count += load_var_box_counts['box_count'] or 0
        headstamp_dict[headstamp_id].box_image_count += load_var_box_counts['image_count'] or 0
    
    # Date Variation-level boxes
    for headstamp_id, ids in headstamp_related_ids.items():
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
        
        headstamp_dict[headstamp_id].box_count += date_var_box_counts['box_count'] or 0
        headstamp_dict[headstamp_id].box_image_count += date_var_box_counts['image_count'] or 0
    
    # Initialize counts for headstamps without data
    for headstamp in headstamps:
        if not hasattr(headstamp, 'load_count'):
            headstamp.load_count = 0
            headstamp.load_image_count = 0
        if not hasattr(headstamp, 'date_count'):
            headstamp.date_count = 0
            headstamp.date_image_count = 0
        if not hasattr(headstamp, 'var_count'):
            headstamp.var_count = 0
            headstamp.var_image_count = 0
        if not hasattr(headstamp, 'date_var_count'):
            headstamp.date_var_count = 0
            headstamp.date_var_image_count = 0
    
    # Get boxes directly associated with this manufacturer
    direct_boxes = Box.objects.filter(
        content_type=manufacturer_content_type,
        object_id=manufacturer.pk
    ).order_by('bid')
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'country': country,
        'manufacturer': manufacturer,
        'headstamps': headstamps,
        'direct_boxes': direct_boxes,
        'manufacturer_content_type': manufacturer_content_type,
    }
    
    return render(request, 'collection/manufacturer_detail.html', context)

def manufacturer_create(request, caliber_code, country_id):
    """View for creating a new manufacturer"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    country = get_object_or_404(Country, id=country_id, caliber=caliber)
    
    if request.method == 'POST':
        form = ManufacturerForm(request.POST)
        if form.is_valid():
            manufacturer = form.save(commit=False)
            manufacturer.country = country
            
            # Check for uniqueness constraint violation
            if Manufacturer.objects.filter(country=country, code=manufacturer.code).exists():
                messages.error(
                    request, 
                    f"Cannot create manufacturer with code '{manufacturer.code}' because a manufacturer with "
                    f"this code already exists in {country.name}."
                )
                return render(request, 'collection/manufacturer_form.html', {
                    'caliber': caliber,
                    'all_calibers': all_calibers,
                    'form': form,
                    'country': country,
                    'title': f'Add New Manufacturer to {country.name}',
                    'submit_text': 'Create Manufacturer',
                })
            
            manufacturer.save()
            messages.success(request, f"Manufacturer '{manufacturer.code}' was created successfully.")
            return redirect('manufacturer_detail', caliber_code=caliber_code, manufacturer_id=manufacturer.id)
    else:
        form = ManufacturerForm()
    
    return render(request, 'collection/manufacturer_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'country': country,
        'title': f'Add New Manufacturer to {country.name}',
        'submit_text': 'Create Manufacturer',
    })


def manufacturer_update(request, caliber_code, manufacturer_id):
    """View for updating a manufacturer"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id, country__caliber=caliber)
    country = manufacturer.country
    
    if request.method == 'POST':
        form = ManufacturerForm(request.POST, instance=manufacturer)
        if form.is_valid():
            updated_manufacturer = form.save(commit=False)
            
            # Check for uniqueness constraint violation, but exclude the current manufacturer
            if Manufacturer.objects.filter(
                country=country, 
                code=updated_manufacturer.code
            ).exclude(id=manufacturer.id).exists():
                messages.error(
                    request, 
                    f"Cannot update manufacturer with code '{updated_manufacturer.code}' because a manufacturer with "
                    f"this code already exists in {country.name}."
                )
                return render(request, 'collection/manufacturer_form.html', {
                    'caliber': caliber,
                    'all_calibers': all_calibers,
                    'form': form,
                    'manufacturer': manufacturer,
                    'country': country,
                    'title': f'Edit Manufacturer: {manufacturer.code}',
                    'submit_text': 'Update Manufacturer',
                })
            
            updated_manufacturer.save()
            messages.success(request, f"Manufacturer '{updated_manufacturer.code}' was updated successfully.")
            return redirect('manufacturer_detail', caliber_code=caliber_code, manufacturer_id=updated_manufacturer.id)
    else:
        form = ManufacturerForm(instance=manufacturer)
    
    return render(request, 'collection/manufacturer_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Edit Manufacturer: {manufacturer.code}',
        'submit_text': 'Update Manufacturer',
    })


def manufacturer_delete(request, caliber_code, manufacturer_id):
    """View for deleting a manufacturer"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id, country__caliber=caliber)
    country = manufacturer.country
    
    # Check if there are any dependent headstamps
    has_headstamps = Headstamp.objects.filter(manufacturer=manufacturer).exists()
    has_headstamps_as_primary = Headstamp.objects.filter(primary_manufacturer=manufacturer).exists()
    
    # Check if there are any direct boxes attached
    manufacturer_content_type = ContentType.objects.get_for_model(Manufacturer)
    has_boxes = Box.objects.filter(content_type=manufacturer_content_type, object_id=manufacturer.pk).exists()
    
    # Process notes for display in the template
    processed_notes = process_notes(manufacturer.note)
    
    if request.method == 'POST':
        if has_headstamps:
            messages.error(request, f"Cannot delete '{manufacturer.code}' because it has headstamps associated with it. Remove the headstamps first.")
            return redirect('manufacturer_detail', caliber_code=caliber_code, manufacturer_id=manufacturer.id)
        
        if has_headstamps_as_primary:
            messages.error(request, f"Cannot delete '{manufacturer.code}' because it is set as the primary manufacturer for some headstamps. Update those headstamps first.")
            return redirect('manufacturer_detail', caliber_code=caliber_code, manufacturer_id=manufacturer.id)
        
        if has_boxes:
            messages.error(request, f"Cannot delete '{manufacturer.code}' because it has boxes directly associated with it. Remove the boxes first.")
            return redirect('manufacturer_detail', caliber_code=caliber_code, manufacturer_id=manufacturer.id)
            
        manufacturer_code = manufacturer.code
        manufacturer.delete()
        messages.success(request, f"Manufacturer '{manufacturer_code}' was deleted successfully.")
        return redirect('country_detail', caliber_code=caliber_code, country_id=country.id)
    
    return render(request, 'collection/manufacturer_confirm_delete.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Delete Manufacturer: {manufacturer.code}',
        'has_headstamps': has_headstamps,
        'has_headstamps_as_primary': has_headstamps_as_primary,
        'has_boxes': has_boxes,
        'can_delete': not (has_headstamps or has_headstamps_as_primary or has_boxes),
        'manufacturer_notes': processed_notes,
    })

def manufacturer_move(request, caliber_code, manufacturer_id):
    """View for moving a manufacturer to a different country"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    manufacturer = get_object_or_404(Manufacturer, id=manufacturer_id, country__caliber=caliber)
    current_country = manufacturer.country
    
    if request.method == 'POST':
        form = ManufacturerMoveForm(request.POST, caliber=caliber)
        if form.is_valid():
            new_country = form.cleaned_data['new_country']
            
            # Don't do anything if the country hasn't changed
            if new_country == current_country:
                messages.info(request, f"'{manufacturer.code}' is already in {current_country.name}.")
                return redirect('manufacturer_detail', caliber_code=caliber_code, manufacturer_id=manufacturer.id)
            
            # Check for uniqueness constraint violation
            if Manufacturer.objects.filter(country=new_country, code=manufacturer.code).exists():
                # There's already a manufacturer with the same code in the target country
                messages.error(
                    request, 
                    f"Cannot move '{manufacturer.code}' to {new_country.name} because a manufacturer with "
                    f"this code already exists there."
                )
                return render(request, 'collection/manufacturer_move_form.html', {
                    'caliber': caliber,
                    'all_calibers': all_calibers,
                    'form': form,
                    'manufacturer': manufacturer,
                    'current_country': current_country,
                    'title': f'Move Manufacturer: {manufacturer.code}',
                    'submit_text': 'Move Manufacturer',
                })
            
            # Update the manufacturer's country
            old_country_name = manufacturer.country.name
            manufacturer.country = new_country
            manufacturer.save()
            
            messages.success(
                request, 
                f"Manufacturer '{manufacturer.code}' was moved from {old_country_name} to {new_country.name}."
            )
            return redirect('manufacturer_detail', caliber_code=caliber_code, manufacturer_id=manufacturer.id)
    else:
        form = ManufacturerMoveForm(caliber=caliber)
    
    return render(request, 'collection/manufacturer_move_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'manufacturer': manufacturer,
        'current_country': current_country,
        'title': f'Move Manufacturer: {manufacturer.code}',
        'submit_text': 'Move Manufacturer',
    })