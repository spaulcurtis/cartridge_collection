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
    

def headstamp_header_search(request, caliber_code):
    """
    Search for headstamps by code or name within the current caliber.
    Redirects to the advanced search with appropriate parameters.
    """
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get search parameters
    query = request.GET.get('q', '').strip()  # For backward compatibility with header search
    
    if query:
        # Redirect to advanced search with parameters set to search both code and name
        from django.urls import reverse
        from urllib.parse import urlencode
        
        # Prepare query parameters for advanced search
        query_params = {
            'headstamp_code': query,           # Search in code
            'headstamp_name': query,           # Search in name
            'search_operator': 'or',           # Match either code or name
            'code_match_type': 'contains',     # Default to contains
            'name_match_type': 'contains',     # Default to contains
        }
        
        # Build URL for redirect
        url = reverse('headstamp_search', kwargs={'caliber_code': caliber_code})
        if query_params:
            url += f'?{urlencode(query_params)}'
        
        return redirect(url)
    
    # If no query is provided, just redirect to the advanced search page
    return redirect('headstamp_search', caliber_code=caliber_code)


def load_search(request, caliber_code):
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
    
    # Variables to store selected names for display
    selected_country_name = ''
    selected_manufacturer_name = ''
    selected_load_type_name = ''
    
    # If a country is selected, get its manufacturers and name
    if search_params['country_id']:
        try:
            country_id = int(search_params['country_id'])
            country = Country.objects.get(id=country_id, caliber=caliber)
            manufacturers = Manufacturer.objects.filter(country_id=country_id).order_by('code')
            selected_country_name = country.name
        except (ValueError, TypeError, Country.DoesNotExist):
            pass
    
    # If a manufacturer is selected, get its name
    if search_params['manufacturer_id']:
        try:
            manufacturer_id = int(search_params['manufacturer_id'])
            manufacturer = Manufacturer.objects.get(id=manufacturer_id)
            selected_manufacturer_name = f"{manufacturer.code}" if not manufacturer.name else f"{manufacturer.code} - {manufacturer.name}"
        except (ValueError, TypeError, Manufacturer.DoesNotExist):
            pass
    
    # If a load type is selected, get its name
    if search_params['load_type_id']:
        try:
            load_type_id = int(search_params['load_type_id'])
            load_type = LoadType.objects.get(id=load_type_id)
            selected_load_type_name = load_type.display_name
        except (ValueError, TypeError, LoadType.DoesNotExist):
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
        'selected_country_name': selected_country_name,
        'selected_manufacturer_name': selected_manufacturer_name,
        'selected_load_type_name': selected_load_type_name,
    }
    
    return render(request, 'collection/load_search.html', context)


def manufacturer_search(request, caliber_code):
    """Advanced search view for manufacturers."""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get available countries for filtering
    countries = Country.objects.filter(caliber=caliber).order_by('name')
    
    # Store search parameters
    search_params = {
        'country_id': request.GET.get('country_id', ''),
        'code': request.GET.get('code', ''),
        'code_match_type': request.GET.get('code_match_type', 'contains'),
        'code_case_sensitive': request.GET.get('code_case_sensitive', '') == 'on',
        'name': request.GET.get('name', ''),
        'notes': request.GET.get('notes', ''),
    }
    
    # Initialize search results and selected country name
    results = None
    selected_country_name = ''
    
    # Determine if search was performed
    performed_search = any(
        v for k, v in search_params.items() 
        if k not in ['code_match_type', 'code_case_sensitive'] and v
    )
    
    if performed_search:
        # Start with all manufacturers for this caliber
        query = Manufacturer.objects.filter(
            country__caliber=caliber
        ).select_related('country')
        
        # Apply country filter if provided
        if search_params['country_id']:
            try:
                country_id = int(search_params['country_id'])
                country = Country.objects.get(id=country_id, caliber=caliber)
                query = query.filter(country_id=country_id)
                selected_country_name = country.name
            except (ValueError, TypeError, Country.DoesNotExist):
                pass
        
        # Apply code search if provided
        if search_params['code']:
            code = search_params['code']
            
            # Apply case sensitivity if requested
            if not search_params['code_case_sensitive']:
                if search_params['code_match_type'] == 'startswith':
                    query = query.filter(code__istartswith=code)
                else:  # contains
                    query = query.filter(code__icontains=code)
            else:
                if search_params['code_match_type'] == 'startswith':
                    query = query.filter(code__startswith=code)
                else:  # contains
                    query = query.filter(code__contains=code)
        
        # Apply name search (always case insensitive)
        if search_params['name']:
            query = query.filter(name__icontains=search_params['name'])
        
        # Apply notes search (always case insensitive)
        if search_params['notes']:
            query = query.filter(note__icontains=search_params['notes'])
        
        # Annotate with counts for related items
        from django.db.models import Count
        query = query.annotate(
            headstamp_count=Count('headstamps', distinct=True),
            # Count loads through headstamps
            load_count=Count('headstamps__loads', distinct=True)
        )
        
        # Order results
        results = query.order_by('country__name', 'code')
        
        # Post-process results to add box counts using the total_box_count method
        # This is more efficient than trying to do complex ContentType queries
        for manufacturer in results:
            manufacturer.box_count = manufacturer.total_box_count()
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'countries': countries,
        'search_params': search_params,
        'results': results,
        'performed_search': performed_search,
        'selected_country_name': selected_country_name,
    }
    
    return render(request, 'collection/manufacturer_search.html', context)


def headstamp_search(request, caliber_code):
    """Advanced search view for headstamps."""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get available filtering options
    countries = Country.objects.filter(caliber=caliber).order_by('name')
    manufacturers = []
    
    # Store search parameters
    search_params = {
        'country_id': request.GET.get('country_id', ''),
        'manufacturer_id': request.GET.get('manufacturer_id', ''),
        'headstamp_code': request.GET.get('headstamp_code', ''),
        'headstamp_name': request.GET.get('headstamp_name', ''),
        'code_match_type': request.GET.get('code_match_type', 'contains'),
        'name_match_type': request.GET.get('name_match_type', 'contains'),
        'code_case_sensitive': request.GET.get('code_case_sensitive') == 'on',  # Corrected comparison
        'name_case_sensitive': request.GET.get('name_case_sensitive') == 'on',  # Corrected comparison
        'search_operator': request.GET.get('search_operator', 'or'),
        'notes': request.GET.get('notes', ''),
    }
    
    # Print debug info to console to verify values
    print(f"Code case sensitive checkbox value: {request.GET.get('code_case_sensitive')}")
    print(f"Name case sensitive checkbox value: {request.GET.get('name_case_sensitive')}")
    print(f"Search params for code_case_sensitive: {search_params['code_case_sensitive']}")
    print(f"Search params for name_case_sensitive: {search_params['name_case_sensitive']}")
    
    # Variables to store selected names for display
    selected_country_name = ''
    selected_manufacturer_name = ''
    
    # If a country is selected, get its manufacturers and name
    if search_params['country_id']:
        try:
            country_id = int(search_params['country_id'])
            country = Country.objects.get(id=country_id, caliber=caliber)
            manufacturers = Manufacturer.objects.filter(country_id=country_id).order_by('code')
            selected_country_name = country.name
        except (ValueError, TypeError, Country.DoesNotExist):
            pass
    
    # If a manufacturer is selected, get its name
    if search_params['manufacturer_id']:
        try:
            manufacturer_id = int(search_params['manufacturer_id'])
            manufacturer = Manufacturer.objects.get(id=manufacturer_id)
            selected_manufacturer_name = f"{manufacturer.code}" if not manufacturer.name else f"{manufacturer.code} - {manufacturer.name}"
        except (ValueError, TypeError, Manufacturer.DoesNotExist):
            pass
    
    # Determine if this is coming from the simple search
    from_simple_search = (
        search_params['headstamp_code'] and 
        search_params['headstamp_name'] and 
        search_params['headstamp_code'] == search_params['headstamp_name'] and
        search_params['search_operator'] == 'or'
    )

    # Initialize search results
    results = None
    performed_search = any(
        v for k, v in search_params.items() 
        if k not in ['code_match_type', 'name_match_type', 'code_case_sensitive', 'name_case_sensitive', 'search_operator'] and v
    )
    
    if performed_search:
        # Start with all headstamps for this caliber
        query = Headstamp.objects.filter(
            manufacturer__country__caliber=caliber
        ).select_related(
            'manufacturer',
            'manufacturer__country'
        )
        
        # Apply organization filters
        if search_params['country_id']:
            try:
                country_id = int(search_params['country_id'])
                query = query.filter(manufacturer__country_id=country_id)
            except (ValueError, TypeError):
                pass
        
        if search_params['manufacturer_id']:
            try:
                manufacturer_id = int(search_params['manufacturer_id'])
                query = query.filter(manufacturer_id=manufacturer_id)
            except (ValueError, TypeError):
                pass
        
        # Build property filters based on the search operator (AND or OR)
        from django.db.models import Q
        property_filters = Q()
        
        # Apply headstamp code search if provided
        if search_params['headstamp_code']:
            code = search_params['headstamp_code']
            code_filter = None
            
            # Apply case sensitivity based on checkbox
            if search_params['code_case_sensitive']:
                # Case sensitive search
                if search_params['code_match_type'] == 'startswith':
                    code_filter = Q(code__startswith=code)
                else:  # contains
                    code_filter = Q(code__contains=code)
            else:
                # Case insensitive search
                if search_params['code_match_type'] == 'startswith':
                    code_filter = Q(code__istartswith=code)
                else:  # contains
                    code_filter = Q(code__icontains=code)
            
            if search_params['search_operator'] == 'and':
                query = query.filter(code_filter)
            else:
                property_filters |= code_filter
        
        # Apply headstamp name search if provided
        if search_params['headstamp_name']:
            name = search_params['headstamp_name']
            name_filter = None
            
            # Apply case sensitivity based on checkbox
            if search_params['name_case_sensitive']:
                # Case sensitive search
                if search_params['name_match_type'] == 'startswith':
                    name_filter = Q(name__startswith=name)
                else:  # contains
                    name_filter = Q(name__contains=name)
            else:
                # Case insensitive search
                if search_params['name_match_type'] == 'startswith':
                    name_filter = Q(name__istartswith=name)
                else:  # contains
                    name_filter = Q(name__icontains=name)
            
            if search_params['search_operator'] == 'and':
                query = query.filter(name_filter)
            else:
                property_filters |= name_filter
        
        # Apply notes search (always case insensitive)
        if search_params['notes']:
            notes_filter = Q(note__icontains=search_params['notes'])
            
            if search_params['search_operator'] == 'and':
                query = query.filter(notes_filter)
            else:
                property_filters |= notes_filter
        
        # Apply the combined OR property filters if we're using OR logic and have any property filters
        if search_params['search_operator'] == 'or' and property_filters:
            query = query.filter(property_filters)
        
        # Annotate with count of loads for each headstamp
        from django.db.models import Count
        query = query.annotate(load_count=Count('loads', distinct=True))
        
        # Order results
        results = query.order_by('manufacturer__country__name', 'manufacturer__code', 'code')
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'countries': countries,
        'manufacturers': manufacturers,
        'search_params': search_params,
        'results': results,
        'performed_search': performed_search,
        'selected_country_name': selected_country_name,
        'selected_manufacturer_name': selected_manufacturer_name,
        'from_simple_search': from_simple_search,
        'simple_search_query': search_params['headstamp_code'] if from_simple_search else ''
    }
    
    return render(request, 'collection/headstamp_search.html', context)