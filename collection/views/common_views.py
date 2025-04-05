from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.db.models.functions import Upper, Substr
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, LoadType, Date, Variation, Box, CollectionInfo

def landing(request):
    """Landing page with caliber selection"""
    # Get all calibers
    calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Add dummy artifact counts
    for caliber in calibers:
        if caliber.code == '9mmP':
            caliber.artifact_count = 17240
        elif caliber.code == '765mmP':
            caliber.artifact_count = 56
        else:
            caliber.artifact_count = 107
    
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
        'pk', 'item_type', 'display_text', 'parent_name', 'updated_at'
    ).order_by('-updated_at')[:5]
    
    # Get recent loads with type indicator
    recent_loads = Load.objects.filter(
        headstamp__manufacturer__country__caliber=caliber
    ).annotate(
        item_type=Value('load'),
        display_text=F('cart_id'),
        parent_name=F('headstamp__code')
    ).values(
        'pk', 'item_type', 'display_text', 'parent_name', 'updated_at'
    ).order_by('-updated_at')[:5]
    
    # Get recent dates with type indicator
    recent_dates = Date.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber
    ).annotate(
        item_type=Value('date'),
        display_text=F('cart_id'),
        parent_name=F('load__cart_id')
    ).values(
        'pk', 'item_type', 'display_text', 'parent_name', 'updated_at'
    ).order_by('-updated_at')[:5]
    
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
        'pk', 'item_type', 'display_text', 'updated_at'
    ).order_by('-updated_at')[:5]
    
    # Combine all recent activities
    recent_activities = list(recent_headstamps) + list(recent_loads) + list(recent_dates) + list(recent_boxes)
    # Sort by updated_at in descending order (most recent first)
    recent_activities.sort(key=lambda x: x['updated_at'], reverse=True)
    # Limit to 15 most recent activities
    recent_activities = recent_activities[:15]
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'stats': stats,
        'recent_activities': recent_activities,
    }

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
    Supports separate code and name searches with combined OR logic.
    Letter filtering is additive to any search criteria.
    """
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get search parameters
    query = request.GET.get('q', '').strip()  # For backward compatibility with header search
    code_query = request.GET.get('code_q', '').strip()
    name_query = request.GET.get('name_q', '').strip()
    
    # If query is provided but code/name are not, populate both code and name with query
    if query and not (code_query or name_query):
        code_query = query
        name_query = query
    
    # Base queryset for all headstamps in this caliber
    headstamps = Headstamp.objects.filter(
        manufacturer__country__caliber=caliber
    ).select_related(
        'manufacturer', 'manufacturer__country'
    )
    
    # Build filter conditions
    filter_conditions = Q()
    
    # Apply code search if provided
    if code_query:
        filter_conditions |= Q(code__icontains=code_query)
    
    # Apply name search if provided
    if name_query:
        filter_conditions |= Q(name__icontains=name_query)
    
    # Apply combined search filter if any search criteria exist
    if filter_conditions:
        headstamps = headstamps.filter(filter_conditions)
    
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
        'code_query': code_query,
        'name_query': name_query,
        'results': headstamps,
        'all_calibers': Caliber.objects.all().order_by('order', 'name'),
        'total_count': headstamps.count(),
    }
    
    return render(request, 'collection/headstamp_search_results.html', context)

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


def get_current_caliber(request):
    """Helper function to get the current caliber from session or default to first active one"""
    # Try to get caliber from session
    caliber_code = request.session.get('current_caliber')
    
    # If we have a caliber code in session, try to get that caliber
    if caliber_code:
        try:
            return Caliber.objects.get(code=caliber_code, is_active=True)
        except Caliber.DoesNotExist:
            pass
    
    # Fallback to first active caliber
    active_calibers = Caliber.objects.filter(is_active=True).order_by('order')
    if active_calibers.exists():
        return active_calibers.first()
    
    # Return None if no active calibers found
    return None

def user_guide_view(request):
    """User guide view"""
    context = {}
    
    # Get current caliber for navigation
    caliber = get_current_caliber(request)
    
    # Add caliber to context
    context['caliber'] = caliber
    
    # Get all calibers for dropdown
    context['all_calibers'] = Caliber.objects.all().order_by('order')
    
    return render(request, 'collection/user_guide.html', context)

def support_view(request):
    """Support page view"""
    context = {}
    
    # Get current caliber for navigation
    caliber = get_current_caliber(request)
    
    # Add caliber to context
    context['caliber'] = caliber
    
    # Get all calibers for dropdown
    context['all_calibers'] = Caliber.objects.all().order_by('order')
    
    return render(request, 'collection/support.html', context)

def advanced_search(request, caliber_code):
    """Advanced search view allowing filtering across multiple models."""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get available filtering options
    countries = Country.objects.filter(caliber=caliber).order_by('name')
    manufacturers = []
    load_types = LoadType.objects.all().order_by('-is_common', 'display_name')
    
    # Store search parameters
    search_params = {
        'country_id': request.GET.get('country_id', ''),
        'manufacturer_id': request.GET.get('manufacturer_id', ''),
        'headstamp_code': request.GET.get('headstamp_code', ''),
        'headstamp_match_type': request.GET.get('headstamp_match_type', 'contains'),
        'headstamp_case_sensitive': request.GET.get('headstamp_case_sensitive', '') == 'on',
        'load_type_id': request.GET.get('load_type_id', ''),
        'notes': request.GET.get('notes', ''),
    }
    
    # If a country is selected, get its manufacturers
    if search_params['country_id']:
        try:
            country_id = int(search_params['country_id'])
            manufacturers = Manufacturer.objects.filter(country_id=country_id).order_by('code')
        except (ValueError, TypeError):
            pass
    
    # Initialize search results
    results = None
    performed_search = any(
        v for k, v in search_params.items() 
        if k not in ['headstamp_match_type', 'headstamp_case_sensitive'] and v
    )
    
    if performed_search:
        # Start with all loads for this caliber
        query = Load.objects.filter(
            headstamp__manufacturer__country__caliber=caliber
        ).select_related(
            'headstamp', 
            'headstamp__manufacturer',
            'headstamp__manufacturer__country',
            'load_type'
        )
        
        # Apply filters based on search parameters
        if search_params['country_id']:
            try:
                country_id = int(search_params['country_id'])
                query = query.filter(headstamp__manufacturer__country_id=country_id)
            except (ValueError, TypeError):
                pass
        
        if search_params['manufacturer_id']:
            try:
                manufacturer_id = int(search_params['manufacturer_id'])
                query = query.filter(headstamp__manufacturer_id=manufacturer_id)
            except (ValueError, TypeError):
                pass
        
        if search_params['headstamp_code']:
            headstamp_code = search_params['headstamp_code']
            
            # Apply case sensitivity if requested
            if not search_params['headstamp_case_sensitive']:
                headstamp_code = headstamp_code.lower()
                if search_params['headstamp_match_type'] == 'startswith':
                    query = query.filter(headstamp__code__istartswith=headstamp_code)
                else:  # contains
                    query = query.filter(headstamp__code__icontains=headstamp_code)
            else:
                if search_params['headstamp_match_type'] == 'startswith':
                    query = query.filter(headstamp__code__startswith=headstamp_code)
                else:  # contains
                    query = query.filter(headstamp__code__contains=headstamp_code)
        
        if search_params['load_type_id']:
            try:
                load_type_id = int(search_params['load_type_id'])
                query = query.filter(load_type_id=load_type_id)
            except (ValueError, TypeError):
                pass
        
        if search_params['notes']:
            query = query.filter(note__icontains=search_params['notes'])
        
        # Order by country, manufacturer code, headstamp code, cart_id
        results = query.order_by(
            'headstamp__manufacturer__country__name',
            'headstamp__manufacturer__code',
            'headstamp__code',
            'cart_id'
        )
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'countries': countries,
        'manufacturers': manufacturers,
        'load_types': load_types,
        'search_params': search_params,
        'results': results,
        'performed_search': performed_search,
    }
    
    return render(request, 'collection/advanced_search.html', context)
