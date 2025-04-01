from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.db.models.functions import Upper, Substr
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box, CollectionInfo

def landing(request):
    """Landing page with caliber selection"""
    # Get all calibers
    calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Add dummy artifact counts
    for caliber in calibers:
        if caliber.code == '9mm':
            caliber.artifact_count = 3240
        elif caliber.code == '7.65mm':
            caliber.artifact_count = 1856
        else:
            caliber.artifact_count = 1200
    
    # Get the global collection info
    collection_info = CollectionInfo.get_solo()
    
    context = {
        'calibers': calibers,
        'collection_name': collection_info.name,
        'collection_description': collection_info.description,
    }

    return render(request, 'collection/landing.html', context)

def dashboard(request, caliber_code):
    """Dashboard for a specific caliber with dynamically calculated statistics"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Default theme color if not specified
    if not caliber.theme_color:
        caliber.theme_color = "#3a7ca5"  # Default blue

    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Calculate statistics for this caliber using efficient queries
    stats = {}
    
    # Count countries
    stats['countries'] = Country.objects.filter(caliber=caliber).count()
    
    # Count manufacturers
    stats['manufacturers'] = Manufacturer.objects.filter(country__caliber=caliber).count()
    
    # Count headstamps and headstamp images
    headstamp_stats = Headstamp.objects.filter(
        manufacturer__country__caliber=caliber
    ).aggregate(
        count=Count('id'),
        image_count=Count('id', filter=~Q(image='') & ~Q(image=None))
    )
    stats['headstamps'] = headstamp_stats['count']
    stats['headstamp_images'] = headstamp_stats['image_count']
    
    # Count loads and load images
    load_stats = Load.objects.filter(
        headstamp__manufacturer__country__caliber=caliber
    ).aggregate(
        count=Count('id'),
        image_count=Count('id', filter=~Q(image='') & ~Q(image=None))
    )
    stats['loads'] = load_stats['count']
    stats['load_images'] = load_stats['image_count']
    
    # Count dates and date images
    date_stats = Date.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber
    ).aggregate(
        count=Count('id'),
        image_count=Count('id', filter=~Q(image='') & ~Q(image=None))
    )
    stats['dates'] = date_stats['count']
    stats['date_images'] = date_stats['image_count']
    
    # Count load variations and images
    load_var_stats = Variation.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber,
        load__isnull=False
    ).aggregate(
        count=Count('id'),
        image_count=Count('id', filter=~Q(image='') & ~Q(image=None))
    )
    stats['load_variations'] = load_var_stats['count']
    stats['load_variation_images'] = load_var_stats['image_count']
    
    # Count date variations and images
    date_var_stats = Variation.objects.filter(
        date__load__headstamp__manufacturer__country__caliber=caliber,
        date__isnull=False
    ).aggregate(
        count=Count('id'),
        image_count=Count('id', filter=~Q(image='') & ~Q(image=None))
    )
    stats['date_variations'] = date_var_stats['count']
    stats['date_variation_images'] = date_var_stats['image_count']
    
    # Count boxes and box images
    # Get ContentType IDs for box queries
    from django.contrib.contenttypes.models import ContentType
    country_content_type = ContentType.objects.get_for_model(Country)
    manufacturer_content_type = ContentType.objects.get_for_model(Manufacturer)
    headstamp_content_type = ContentType.objects.get_for_model(Headstamp)
    load_content_type = ContentType.objects.get_for_model(Load)
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get IDs at each level
    country_ids = Country.objects.filter(caliber=caliber).values_list('id', flat=True)
    manufacturer_ids = Manufacturer.objects.filter(country__caliber=caliber).values_list('id', flat=True)
    headstamp_ids = Headstamp.objects.filter(manufacturer__country__caliber=caliber).values_list('id', flat=True)
    load_ids = Load.objects.filter(headstamp__manufacturer__country__caliber=caliber).values_list('id', flat=True)
    date_ids = Date.objects.filter(load__headstamp__manufacturer__country__caliber=caliber).values_list('id', flat=True)
    load_var_ids = Variation.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber, 
        load__isnull=False
    ).values_list('id', flat=True)
    date_var_ids = Variation.objects.filter(
        date__load__headstamp__manufacturer__country__caliber=caliber, 
        date__isnull=False
    ).values_list('id', flat=True)
    
    # Count boxes at each level using a combined query
    box_stats = Box.objects.filter(
        # Country level boxes
        Q(content_type=country_content_type, object_id__in=country_ids) |
        # Manufacturer level boxes
        Q(content_type=manufacturer_content_type, object_id__in=manufacturer_ids) |
        # Headstamp level boxes
        Q(content_type=headstamp_content_type, object_id__in=headstamp_ids) |
        # Load level boxes
        Q(content_type=load_content_type, object_id__in=load_ids) |
        # Date level boxes
        Q(content_type=date_content_type, object_id__in=date_ids) |
        # Variation level boxes (both types)
        Q(content_type=variation_content_type, object_id__in=list(load_var_ids) + list(date_var_ids))
    ).aggregate(
        count=Count('id'),
        image_count=Count('id', filter=~Q(image='') & ~Q(image=None))
    )
    
    stats['boxes'] = box_stats['count']
    stats['box_images'] = box_stats['image_count']
    
    # Create a combined recent activity timeline
    # Collect recent activities from different model types,
    # limiting to 15 recent items to keep performance impact minimal
    from itertools import islice
    from django.db.models import F, Value
    from django.db.models.functions import Concat
    
    # Get recent headstamps with type indicator
    recent_headstamps = Headstamp.objects.filter(
        manufacturer__country__caliber=caliber
    ).annotate(
        item_type=Value('headstamp'),
        display_text=F('code'),
        parent_name=F('manufacturer__code')
    ).values(
        'pk', 'item_type', 'display_text', 'parent_name', 'created_at'
    ).order_by('-created_at')[:5]
    
    # Get recent loads with type indicator
    recent_loads = Load.objects.filter(
        headstamp__manufacturer__country__caliber=caliber
    ).annotate(
        item_type=Value('load'),
        display_text=F('cart_id'),
        parent_name=F('headstamp__code')
    ).values(
        'pk', 'item_type', 'display_text', 'parent_name', 'created_at'
    ).order_by('-created_at')[:5]
    
    # Get recent dates with type indicator
    recent_dates = Date.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber
    ).annotate(
        item_type=Value('date'),
        display_text=F('cart_id'),
        parent_name=F('load__cart_id')
    ).values(
        'pk', 'item_type', 'display_text', 'parent_name', 'created_at'
    ).order_by('-created_at')[:5]
    
    # Get recent boxes
    from django.contrib.contenttypes.models import ContentType
    country_content_type = ContentType.objects.get_for_model(Country)
    manufacturer_content_type = ContentType.objects.get_for_model(Manufacturer)
    headstamp_content_type = ContentType.objects.get_for_model(Headstamp)
    load_content_type = ContentType.objects.get_for_model(Load)
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get IDs at each level for filtering boxes
    country_ids = Country.objects.filter(caliber=caliber).values_list('id', flat=True)
    manufacturer_ids = Manufacturer.objects.filter(country__caliber=caliber).values_list('id', flat=True)
    headstamp_ids = Headstamp.objects.filter(manufacturer__country__caliber=caliber).values_list('id', flat=True)
    load_ids = Load.objects.filter(headstamp__manufacturer__country__caliber=caliber).values_list('id', flat=True)
    date_ids = Date.objects.filter(load__headstamp__manufacturer__country__caliber=caliber).values_list('id', flat=True)
    load_var_ids = Variation.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber, 
        load__isnull=False
    ).values_list('id', flat=True)
    date_var_ids = Variation.objects.filter(
        date__load__headstamp__manufacturer__country__caliber=caliber, 
        date__isnull=False
    ).values_list('id', flat=True)
    
    recent_boxes = Box.objects.filter(
        Q(content_type=country_content_type, object_id__in=country_ids) |
        Q(content_type=manufacturer_content_type, object_id__in=manufacturer_ids) |
        Q(content_type=headstamp_content_type, object_id__in=headstamp_ids) |
        Q(content_type=load_content_type, object_id__in=load_ids) |
        Q(content_type=date_content_type, object_id__in=date_ids) |
        Q(content_type=variation_content_type, object_id__in=list(load_var_ids) + list(date_var_ids))
    ).annotate(
        item_type=Value('box'),
        display_text=F('bid'),
    ).values(
        'pk', 'item_type', 'display_text', 'created_at'
    ).order_by('-created_at')[:5]
    
    # Combine all recent activities
    recent_activities = list(recent_headstamps) + list(recent_loads) + list(recent_dates) + list(recent_boxes)
    # Sort by created_at in descending order (most recent first)
    recent_activities.sort(key=lambda x: x['created_at'], reverse=True)
    # Limit to 15 most recent activities
    recent_activities = recent_activities[:15]
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'stats': stats,
        'recent_activities': recent_activities,
    }

    # # Get recent items (limited to 5 each)
    # recent_headstamps = Headstamp.objects.filter(
    #     manufacturer__country__caliber=caliber
    # ).order_by('-created_at')[:5]
    
    # recent_loads = Load.objects.filter(
    #     headstamp__manufacturer__country__caliber=caliber
    # ).order_by('-created_at')[:5]
    
    # recent_boxes = Box.objects.filter(
    #     Q(content_type=country_content_type, object_id__in=country_ids) |
    #     Q(content_type=manufacturer_content_type, object_id__in=manufacturer_ids) |
    #     Q(content_type=headstamp_content_type, object_id__in=headstamp_ids) |
    #     Q(content_type=load_content_type, object_id__in=load_ids) |
    #     Q(content_type=date_content_type, object_id__in=date_ids) |
    #     Q(content_type=variation_content_type, object_id__in=list(load_var_ids) + list(date_var_ids))
    # ).order_by('-created_at')[:5]
    
    # context = {
    #     'caliber': caliber,
    #     'all_calibers': all_calibers,
    #     'stats': stats,
    #     'recent_headstamps': recent_headstamps,
    #     'recent_loads': recent_loads,
    #     'recent_boxes': recent_boxes,
    # }

    return render(request, 'collection/dashboard.html', context)


def record_search(request, caliber_code):
    """
    Search for a specific record by ID (cart_id for L/D/V or bid for B) 
    and redirect to its detail page if found within the current caliber.
    If not found, stay on the current page.
    """
    caliber = get_object_or_404(Caliber, code=caliber_code)
    rec_id = request.GET.get('id', '').strip().upper()  # Standardize to uppercase
    
    # Remember the current page to return to if no record is found
    current_page = request.META.get('HTTP_REFERER')
    
    if not rec_id:
        messages.warning(request, 'Please enter a record ID.')
        # Return to referring page if available, otherwise to dashboard
        return redirect(current_page if current_page else 'dashboard', caliber_code=caliber.code)
    
    # First character determines record type
    prefix = rec_id[0] if rec_id else None
    
    search_config = {
        'L': {
            'model': Load, 
            'field': 'cart_id', 
            'redirect': 'load_detail',
            'filter': {'headstamp__manufacturer__country__caliber': caliber}
        },
        'D': {
            'model': Date, 
            'field': 'cart_id', 
            'redirect': 'date_detail',
            'filter': {'load__headstamp__manufacturer__country__caliber': caliber}
        },
        'V': {
            'model': Variation, 
            'field': 'cart_id', 
            'redirect': 'variation_detail',
            'filter': {'load__headstamp__manufacturer__country__caliber': caliber} # This will catch load variations
            # Date variations need separate handling
        },
        'B': {
            'model': Box, 
            'field': 'bid', 
            'redirect': 'box_detail',
            # Boxes need custom filtering based on their content_type and object_id
        }
    }
    
    if prefix in search_config:
        config = search_config[prefix]
        
        try:
            # Special handling for boxes
            if prefix == 'B':
                # This requires determining if the box is related to the current caliber
                # We'll use the parent_caliber method defined in your Box model
                box = Box.objects.get(bid__iexact=rec_id)
                if box.parent_caliber() == caliber:
                    return redirect(config['redirect'], caliber_code=caliber.code, box_id=box.pk)
                else:
                    messages.warning(request, f'Box {rec_id} exists but belongs to a different caliber collection.')
            
            # Special handling for variations that could be attached to loads or dates
            elif prefix == 'V':
                # Try to find a load variation first
                try:
                    variation = Variation.objects.get(
                        cart_id__iexact=rec_id,
                        load__isnull=False,
                        load__headstamp__manufacturer__country__caliber=caliber
                    )
                    return redirect(config['redirect'], caliber_code=caliber.code, variation_id=variation.pk)
                except Variation.DoesNotExist:
                    # Then try to find a date variation
                    variation = Variation.objects.get(
                        cart_id__iexact=rec_id,
                        date__isnull=False,
                        date__load__headstamp__manufacturer__country__caliber=caliber
                    )
                    return redirect(config['redirect'], caliber_code=caliber.code, variation_id=variation.pk)
            
            # Standard handling for other types
            else:
                filters = config['filter'].copy()
                filters[f"{config['field']}__iexact"] = rec_id
                record = config['model'].objects.get(**filters)
                return redirect(config['redirect'], caliber_code=caliber.code, **{f"{config['model'].__name__.lower()}_id": record.pk})
                
        except (config['model'].DoesNotExist, Variation.DoesNotExist):
            pass  # No match found, will display error message
    
    messages.warning(request, f'No record found with ID: {rec_id} in the {caliber.name} collection.')
    
    # Return to referring page if available, otherwise to dashboard
    if current_page:
        return redirect(current_page)
    else:
        return redirect('dashboard', caliber_code=caliber.code)
    

def headstamp_search(request, caliber_code):
    """
    Search for headstamps by code or name within the current caliber.
    If no query is provided, return all headstamps with alphabet navigation.
    """
    caliber = get_object_or_404(Caliber, code=caliber_code)
    query = request.GET.get('q', '').strip()
    
    # Filter headstamps by letter if provided
    letter_filter = request.GET.get('letter', '').upper()
    
    # Base queryset for all headstamps in this caliber
    headstamps = Headstamp.objects.filter(
        manufacturer__country__caliber=caliber
    ).select_related(
        'manufacturer', 'manufacturer__country'
    )
    
    # Apply search filter if query exists
    if query:
        headstamps = headstamps.filter(
            Q(code__icontains=query) | Q(name__icontains=query)
        )
    # Apply letter filter if no query but letter is specified
    elif letter_filter and len(letter_filter) == 1:
        headstamps = headstamps.filter(code__istartswith=letter_filter)
    
    # Get all available first letters for alphabet navigation
    available_letters = Headstamp.objects.filter(
        manufacturer__country__caliber=caliber
    ).annotate(
        first_letter=Upper(Substr('code', 1, 1))
    ).values_list('first_letter', flat=True).distinct().order_by('first_letter')
    
    # Convert QuerySet to list and remove any non-alphabetic characters
    available_letters = [letter for letter in available_letters if letter.isalpha()]
    
    # Order results
    headstamps = headstamps.order_by('code')
    
    context = {
        'caliber': caliber,
        'query': query,
        'letter_filter': letter_filter,
        'results': headstamps,
        'available_letters': available_letters,
        'all_calibers': Caliber.objects.all().order_by('order', 'name'),
        'total_count': headstamps.count(),
    }
    
    return render(request, 'collection/headstamp_search_results.html', context)


def advanced_search(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'title': 'Advanced Search',
        'message': 'This page is under construction'
    })

def add_artifact(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'title': 'Add Artifact',
        'message': 'This page is under construction'
    })

def import_images(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'title': 'Import Images',
        'message': 'This page is under construction'
    })

def documentation(request):
    return render(request, 'collection/placeholder.html', {
        'title': 'Documentation',
        'message': 'Documentation is under construction'
    })

def support(request):
    return render(request, 'collection/placeholder.html', {
        'title': 'Support',
        'message': 'Support page is under construction'
    })

