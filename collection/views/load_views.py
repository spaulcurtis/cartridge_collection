from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
import re
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box, LoadSource, Source
from ..forms.load_forms import LoadForm, LoadSourceForm, LoadMoveForm
from ..utils.note_utils import process_notes

def smart_sort_key(date_obj):
    """
    Generate a sort key for dates that handles numeric lot values intelligently.
    Returns a tuple (year_key, lot_key) for sorting.
    """
    year = date_obj.year or ''
    lot = date_obj.lot_month or ''
    
    def parse_sort_value(value):
        if not value:
            return (0, '')
        
        # Try to extract leading number for numeric sorting
        numeric_match = re.match(r'^(\d+)', str(value))
        if numeric_match:
            # If it starts with a number, sort by that number first, then by the rest
            num = int(numeric_match.group(1))
            remainder = str(value)[len(numeric_match.group(1)):]
            return (1, num, remainder)
        else:
            # Non-numeric, sort alphabetically but after numeric values
            return (2, 0, str(value))
    
    year_key = parse_sort_value(year)
    lot_key = parse_sort_value(lot)
    
    return (year_key, lot_key)

def prepare_grid_data(dates):
    """
    Prepare data for grid view: organize dates by year and lot.
    Returns dict with years as keys and lots as nested dict.
    """
    grid_data = {}
    all_lots = set()
    
    for date in dates:
        year = date.year or 'Unknown'
        lot = date.lot_month or 'Unknown'
        
        if year not in grid_data:
            grid_data[year] = {}
        
        # Handle potential duplicates by storing in a list
        if lot not in grid_data[year]:
            grid_data[year][lot] = []
        
        grid_data[year][lot].append(date)
        all_lots.add(lot)
    
    # Sort years and lots intelligently
    def sort_grid_value(value):
        if value == 'Unknown':
            return (999, '')  # Put Unknown at the end
        return parse_sort_value(value)
    
    def parse_sort_value(value):
        if not value:
            return (0, '')
        
        numeric_match = re.match(r'^(\d+)', str(value))
        if numeric_match:
            num = int(numeric_match.group(1))
            remainder = str(value)[len(numeric_match.group(1)):]
            return (1, num, remainder)
        else:
            return (2, 0, str(value))
    
    # Sort all_lots for column headers
    sorted_lots = sorted(all_lots, key=sort_grid_value)
    
    # Sort years
    sorted_years = sorted(grid_data.keys(), key=sort_grid_value)
    
    # Create ordered grid data
    ordered_grid = {}
    for year in sorted_years:
        ordered_grid[year] = {}
        for lot in sorted_lots:
            if lot in grid_data[year]:
                ordered_grid[year][lot] = grid_data[year][lot]
            else:
                ordered_grid[year][lot] = None  # Empty cell
    
    return {
        'grid_data': ordered_grid,
        'sorted_years': sorted_years,
        'sorted_lots': sorted_lots
    }

def load_detail(request, caliber_code, load_id):
    """View for showing details of a specific load"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get the load
    load = get_object_or_404(Load, id=load_id, headstamp__manufacturer__country__caliber=caliber)
    
    # Get the headstamp, manufacturer and country
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Process notes
    load_notes = process_notes(load.note)
    load.note_has_notes = load_notes['has_notes']
    load.note_public_notes = load_notes['public_notes']
    load.note_confidential_notes = load_notes['confidential_notes']
    load.note_has_confidential = load_notes['has_confidential']
    
    # Get source information
    load_sources = LoadSource.objects.filter(load=load).select_related('source')
    
    # Get ContentType IDs for box queries
    load_content_type = ContentType.objects.get_for_model(Load)
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get dates for this load - use smart sorting
    dates_queryset = Date.objects.filter(load=load)
    dates = list(dates_queryset)  # Convert to list for custom sorting
    dates.sort(key=smart_sort_key)  # Apply smart sorting
    
    # Get load variations for this load
    load_variations = Variation.objects.filter(load=load, date__isnull=True).order_by('cart_id')
    
    # Create a mapping of date_id to date objects for easy reference
    date_dict = {date.id: date for date in dates}
    
    # For each date, gather the related IDs
    date_related_ids = {}
    
    # Date Variation IDs per date
    date_var_query = Variation.objects.filter(
        date__in=dates,
        date__isnull=False
    ).values('date_id', 'id', 'image')
    
    for item in date_var_query:
        date_id = item['date_id']
        var_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if date_id not in date_related_ids:
            date_related_ids[date_id] = {
                'var_ids': []
            }
            
        date_related_ids[date_id]['var_ids'].append(var_id)
        
        # Count date variations
        if not hasattr(date_dict[date_id], 'var_count'):
            date_dict[date_id].var_count = 0
            date_dict[date_id].var_image_count = 0
            
        date_dict[date_id].var_count += 1
        if has_image:
            date_dict[date_id].var_image_count += 1
    
    # Initialize box counts for dates
    for date in dates:
        date.box_count = 0
        date.box_image_count = 0
    
    # Date-level boxes
    date_box_counts = Box.objects.filter(
        content_type=date_content_type,
        object_id__in=[d.id for d in dates]
    ).values('object_id').annotate(
        box_count=Count('id'),
        image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
    )
    
    for item in date_box_counts:
        date_id = item['object_id']
        box_count = item['box_count']
        image_count = item['image_count']
        
        if date_id in date_dict:
            date_dict[date_id].box_count += box_count
            date_dict[date_id].box_image_count += image_count
    
    # Date Variation-level boxes
    for date_id, ids in date_related_ids.items():
        var_ids = ids.get('var_ids', [])
        if not var_ids:
            continue
            
        date_var_box_counts = Box.objects.filter(
            content_type=variation_content_type,
            object_id__in=var_ids
        ).aggregate(
            box_count=Count('id'),
            image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
        )
        
        date_dict[date_id].box_count += date_var_box_counts['box_count'] or 0
        date_dict[date_id].box_image_count += date_var_box_counts['image_count'] or 0
    
    # Initialize counts for dates without data
    for date in dates:
        if not hasattr(date, 'var_count'):
            date.var_count = 0
            date.var_image_count = 0
    
    # Initialize box counts for load variations
    for var in load_variations:
        var.box_count = 0
        var.box_image_count = 0
    
    # Variation-level boxes
    var_box_counts = Box.objects.filter(
        content_type=variation_content_type,
        object_id__in=[v.id for v in load_variations]
    ).values('object_id').annotate(
        box_count=Count('id'),
        image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
    )
    
    for item in var_box_counts:
        var_id = item['object_id']
        box_count = item['box_count']
        image_count = item['image_count']
        
        for var in load_variations:
            if var.id == var_id:
                var.box_count = box_count
                var.box_image_count = image_count
                break
    
    # Get boxes directly associated with this load
    direct_boxes = Box.objects.filter(
        content_type=load_content_type,
        object_id=load.pk
    ).order_by('bid')
    
    # Prepare grid data for dates
    grid_info = prepare_grid_data(dates) if dates else {
        'grid_data': {},
        'sorted_years': [],
        'sorted_lots': []
    }
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'country': country,
        'manufacturer': manufacturer,
        'headstamp': headstamp,
        'load': load,
        'dates': dates,
        'load_variations': load_variations,
        'direct_boxes': direct_boxes,
        'load_content_type': load_content_type,
        'load_sources': load_sources,
        'dates_grid_data': grid_info['grid_data'],
        'dates_sorted_years': grid_info['sorted_years'],
        'dates_sorted_lots': grid_info['sorted_lots'],
    }
    
    return render(request, 'collection/load_detail.html', context)


@login_required
@permission_required('collection.add_load', raise_exception=True)
def load_create(request, caliber_code, headstamp_id):
    """View for creating a new load"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    headstamp = get_object_or_404(Headstamp, id=headstamp_id, manufacturer__country__caliber=caliber)
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    if request.method == 'POST':
        form = LoadForm(request.POST, request.FILES)
        if form.is_valid():
            load = form.save(commit=False)
            load.headstamp = headstamp
            load.save()
            messages.success(request, f"Load '{load.cart_id}' was created successfully.")
            return redirect('load_detail', caliber_code=caliber_code, load_id=load.id)
    else:
        form = LoadForm()
    
    return render(request, 'collection/load_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Add New Load to {headstamp.code}',
        'submit_text': 'Create Load',
    })


@login_required
@permission_required('collection.change_load', raise_exception=True)
def load_update(request, caliber_code, load_id):
    """View for updating a load"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    load = get_object_or_404(Load, id=load_id, headstamp__manufacturer__country__caliber=caliber)
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Get source information
    load_sources = LoadSource.objects.filter(load=load).select_related('source')
    
    if request.method == 'POST':
        form = LoadForm(request.POST, request.FILES, instance=load)
        if form.is_valid():
            form.save()
            messages.success(request, f"Load '{load.cart_id}' was updated successfully.")
            return redirect('load_detail', caliber_code=caliber_code, load_id=load.id)

    else:
        form = LoadForm(instance=load)
        
    # Source form for adding new sources
    source_form = LoadSourceForm()
    
    return render(request, 'collection/load_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'source_form': source_form,
        'load': load,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Edit Load: {load.cart_id}',
        'submit_text': 'Update Load',
        'load_sources': load_sources,
    })


@login_required
@permission_required('collection.delete_load', raise_exception=True)
def load_delete(request, caliber_code, load_id):
    """View for deleting a load"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    load = get_object_or_404(Load, id=load_id, headstamp__manufacturer__country__caliber=caliber)
    headstamp = load.headstamp
    manufacturer = headstamp.manufacturer
    country = manufacturer.country
    
    # Check if there are any dependent dates
    has_dates = Date.objects.filter(load=load).exists()
    
    # Check if there are any dependent variations
    has_variations = Variation.objects.filter(load=load).exists()
    
    # Check if there are any direct boxes attached
    load_content_type = ContentType.objects.get_for_model(Load)
    has_boxes = Box.objects.filter(content_type=load_content_type, object_id=load.pk).exists()
    
    # Process notes for display in the template
    processed_notes = process_notes(load.note)
    
    if request.method == 'POST':
        if has_dates:
            messages.error(request, f"Cannot delete '{load.cart_id}' because it has dates associated with it. Remove the dates first.")
            return redirect('load_detail', caliber_code=caliber_code, load_id=load.id)
        
        if has_variations:
            messages.error(request, f"Cannot delete '{load.cart_id}' because it has variations associated with it. Remove the variations first.")
            return redirect('load_detail', caliber_code=caliber_code, load_id=load.id)
        
        if has_boxes:
            messages.error(request, f"Cannot delete '{load.cart_id}' because it has boxes directly associated with it. Remove the boxes first.")
            return redirect('load_detail', caliber_code=caliber_code, load_id=load.id)
            
        load_cart_id = load.cart_id
        load.delete()
        messages.success(request, f"Load '{load_cart_id}' was deleted successfully.")
        return redirect('headstamp_detail', caliber_code=caliber_code, headstamp_id=headstamp.id)
    
    return render(request, 'collection/load_confirm_delete.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'load': load,
        'headstamp': headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Delete Load: {load.cart_id}',
        'has_dates': has_dates,
        'has_variations': has_variations,
        'has_boxes': has_boxes,
        'can_delete': not (has_dates or has_variations or has_boxes),
        'load_notes': processed_notes,
    })


def load_add_source(request, caliber_code, load_id):
    """View for adding a source to a load"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    load = get_object_or_404(Load, id=load_id, headstamp__manufacturer__country__caliber=caliber)
    
    if request.method == 'POST':
        form = LoadSourceForm(request.POST)
        if form.is_valid():
            source_link = form.save(commit=False)
            source_link.load = load
            source_link.save()
            messages.success(request, f"Source '{source_link.source.name}' was added to load.")
            return redirect('load_update', caliber_code=caliber_code, load_id=load.id)
    
    # If form is invalid, the load_update view will handle it
    return redirect('load_update', caliber_code=caliber_code, load_id=load.id)


def load_remove_source(request, caliber_code, load_id, source_id):
    """View for removing a source from a load"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    load = get_object_or_404(Load, id=load_id, headstamp__manufacturer__country__caliber=caliber)
    source_link = get_object_or_404(LoadSource, id=source_id, load=load)
    
    if request.method == 'POST':
        source_name = source_link.source.name
        source_link.delete()
        messages.success(request, f"Source '{source_name}' was removed from load.")
    
    return redirect('load_update', caliber_code=caliber_code, load_id=load.id)

def load_move(request, caliber_code, load_id):
    """View for moving a load to a different headstamp"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    load = get_object_or_404(Load, id=load_id, headstamp__manufacturer__country__caliber=caliber)
    current_headstamp = load.headstamp
    manufacturer = current_headstamp.manufacturer
    country = manufacturer.country
    
    if request.method == 'POST':
        form = LoadMoveForm(request.POST, caliber=caliber)
        if form.is_valid():
            new_headstamp = form.cleaned_data['new_headstamp']
            
            # Don't do anything if the headstamp hasn't changed
            if new_headstamp == current_headstamp:
                messages.info(request, f"Load '{load.cart_id}' is already assigned to headstamp '{current_headstamp.code}'.")
                return redirect('load_detail', caliber_code=caliber_code, load_id=load.id)
            
            # Update the load's headstamp
            old_headstamp_code = current_headstamp.code
            load.headstamp = new_headstamp
            load.save()
            
            messages.success(
                request, 
                f"Load '{load.cart_id}' was moved from headstamp '{old_headstamp_code}' to '{new_headstamp.code}'."
            )
            return redirect('load_detail', caliber_code=caliber_code, load_id=load.id)
    else:
        form = LoadMoveForm(caliber=caliber)
        
        # Customize the headstamp display to show manufacturer, country, and headstamp code
        from django.forms.models import ModelChoiceIterator
        
        class CustomModelChoiceIterator(ModelChoiceIterator):
            def choice(self, obj):
                manufacturer_info = f"{obj.manufacturer.country.name} - {obj.manufacturer.code}"
                if obj.manufacturer.name:
                    manufacturer_info += f" - {obj.manufacturer.name[:30]}"
                return (obj.id, f"{manufacturer_info} | {obj.code}")
        
        form.fields['new_headstamp'].widget.choices = CustomModelChoiceIterator(form.fields['new_headstamp'])
    
    return render(request, 'collection/load_move_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'load': load,
        'current_headstamp': current_headstamp,
        'manufacturer': manufacturer,
        'country': country,
        'title': f'Move Load: {load.cart_id}',
        'submit_text': 'Move Load',
    })