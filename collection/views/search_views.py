from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.db.models.functions import Upper, Substr
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, LoadType, BulletType, CaseType, PrimerType, PAColor, Date, Variation, Box, CollectionInfo


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
    
    # Get sort parameters
    sort_by = request.GET.get('sort_by', 'cart_id')
    sort_dir = request.GET.get('sort_dir', 'asc')
    
    # Get available filtering options
    countries = Country.objects.filter(caliber=caliber).order_by('name')
    manufacturers = []
    load_types = LoadType.objects.all().order_by('-is_common', 'display_name')
    bullet_types = BulletType.objects.all().order_by('-is_common', 'display_name')
    case_types = CaseType.objects.all().order_by('-is_common', 'display_name')
    primer_types = PrimerType.objects.all().order_by('-is_common', 'display_name')
    pa_colors = PAColor.objects.all().order_by('-is_common', 'display_name')
    
    # Store search parameters
    search_params = {
        'country_id': request.GET.get('country_id', ''),
        'manufacturer_id': request.GET.get('manufacturer_id', ''),
        'headstamp_code': request.GET.get('headstamp_code', ''),
        'headstamp_match_type': request.GET.get('headstamp_match_type', 'contains'),
        'load_type_id': request.GET.get('load_type_id', ''),
        'bullet_id': request.GET.get('bullet_id', ''),
        'is_magnetic': request.GET.get('is_magnetic', ''),
        'case_type_id': request.GET.get('case_type_id', ''),
        'primer_id': request.GET.get('primer_id', ''),
        'pa_color_id': request.GET.get('pa_color_id', ''),
        'description': request.GET.get('description', ''),
        'description_match_type': request.GET.get('description_match_type', 'contains'),
        'notes': request.GET.get('notes', ''),
        'search_operator': request.GET.get('search_operator', 'or'),
        'sort_by': sort_by,
        'sort_dir': sort_dir,
    }
    
    # Variables to store selected names for display
    selected_country_name = ''
    selected_manufacturer_name = ''
    selected_load_type_name = ''
    selected_bullet_name = ''
    selected_case_type_name = ''
    selected_primer_name = ''
    selected_pa_color_name = ''
    
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
    
    # If a bullet type is selected, get its name
    if search_params['bullet_id']:
        try:
            bullet_id = int(search_params['bullet_id'])
            bullet = BulletType.objects.get(id=bullet_id)
            selected_bullet_name = bullet.display_name
        except (ValueError, TypeError, BulletType.DoesNotExist):
            pass
    
    # If a case type is selected, get its name
    if search_params['case_type_id']:
        try:
            case_type_id = int(search_params['case_type_id'])
            case_type = CaseType.objects.get(id=case_type_id)
            selected_case_type_name = case_type.display_name
        except (ValueError, TypeError, CaseType.DoesNotExist):
            pass
    
    # If a primer type is selected, get its name
    if search_params['primer_id']:
        try:
            primer_id = int(search_params['primer_id'])
            primer = PrimerType.objects.get(id=primer_id)
            selected_primer_name = primer.display_name
        except (ValueError, TypeError, PrimerType.DoesNotExist):
            pass
    
    # If a PA color is selected, get its name
    if search_params['pa_color_id']:
        try:
            pa_color_id = int(search_params['pa_color_id'])
            pa_color = PAColor.objects.get(id=pa_color_id)
            selected_pa_color_name = pa_color.display_name
        except (ValueError, TypeError, PAColor.DoesNotExist):
            pass
    
    # Initialize search results
    results = None
    performed_search = any(
        v for k, v in search_params.items() 
        if k not in ['headstamp_match_type', 'description_match_type', 'search_operator', 'sort_by', 'sort_dir'] and v
    )
    
    if performed_search:
        # Start with all loads for this caliber
        query = Load.objects.filter(
            headstamp__manufacturer__country__caliber=caliber
        ).select_related(
            'headstamp', 
            'headstamp__manufacturer',
            'headstamp__manufacturer__country',
            'load_type',
            'bullet',
            'case_type',
            'primer',
            'pa_color'
        )
        
        # Apply organization filters
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

        # Build property filters based on the search operator (AND or OR)
        from django.db.models import Q
        property_filters = Q()
                
        # Apply headstamp code search if provided
        if search_params['headstamp_code']:
            headstamp_code = search_params['headstamp_code']
            headstamp_filter = None
            
            if search_params['headstamp_match_type'] == 'is_exactly':
                # Case sensitive exact match
                headstamp_filter = Q(headstamp__code=headstamp_code)
            elif search_params['headstamp_match_type'] == 'startswith':
                # Case insensitive starts with
                headstamp_filter = Q(headstamp__code__istartswith=headstamp_code)
            else:  # contains (default)
                # Case insensitive contains
                headstamp_filter = Q(headstamp__code__icontains=headstamp_code)
            
            if search_params['search_operator'] == 'and':
                query = query.filter(headstamp_filter)
            else:  # 'or' is default
                property_filters |= headstamp_filter
        
        # Apply load type filter if provided
        if search_params['load_type_id']:
            try:
                load_type_id = int(search_params['load_type_id'])
                load_type_filter = Q(load_type_id=load_type_id)
                
                if search_params['search_operator'] == 'and':
                    query = query.filter(load_type_filter)
                else:  # 'or' is default
                    property_filters |= load_type_filter
            except (ValueError, TypeError):
                pass
        
        # Apply bullet type filter if provided
        if search_params['bullet_id']:
            try:
                bullet_id = int(search_params['bullet_id'])
                bullet_filter = Q(bullet_id=bullet_id)
                
                if search_params['search_operator'] == 'and':
                    query = query.filter(bullet_filter)
                else:  # 'or' is default
                    property_filters |= bullet_filter
            except (ValueError, TypeError):
                pass
        
        # Apply is_magnetic filter if provided
        if search_params['is_magnetic']:
            is_magnetic = search_params['is_magnetic'] == 'true'
            magnetic_filter = Q(is_magnetic=is_magnetic)
            
            if search_params['search_operator'] == 'and':
                query = query.filter(magnetic_filter)
            else:  # 'or' is default
                property_filters |= magnetic_filter
        
        # Apply case type filter if provided
        if search_params['case_type_id']:
            try:
                case_type_id = int(search_params['case_type_id'])
                case_filter = Q(case_type_id=case_type_id)
                
                if search_params['search_operator'] == 'and':
                    query = query.filter(case_filter)
                else:  # 'or' is default
                    property_filters |= case_filter
            except (ValueError, TypeError):
                pass
        
        # Apply primer type filter if provided
        if search_params['primer_id']:
            try:
                primer_id = int(search_params['primer_id'])
                primer_filter = Q(primer_id=primer_id)
                
                if search_params['search_operator'] == 'and':
                    query = query.filter(primer_filter)
                else:  # 'or' is default
                    property_filters |= primer_filter
            except (ValueError, TypeError):
                pass
        
        # Apply PA color filter if provided
        if search_params['pa_color_id']:
            try:
                pa_color_id = int(search_params['pa_color_id'])
                pa_color_filter = Q(pa_color_id=pa_color_id)
                
                if search_params['search_operator'] == 'and':
                    query = query.filter(pa_color_filter)
                else:  # 'or' is default
                    property_filters |= pa_color_filter
            except (ValueError, TypeError):
                pass
        
        # Apply description search if provided
        if search_params['description']:
            description = search_params['description']
            description_filter = None
            
            if search_params['description_match_type'] == 'startswith':
                # Case insensitive starts with
                description_filter = Q(description__istartswith=description)
            else:  # contains (default)
                # Case insensitive contains
                description_filter = Q(description__icontains=description)
            
            if search_params['search_operator'] == 'and':
                query = query.filter(description_filter)
            else:  # 'or' is default
                property_filters |= description_filter
        
        # Apply notes search (always case insensitive)
        if search_params['notes']:
            notes_filter = Q(note__icontains=search_params['notes'])
            
            if search_params['search_operator'] == 'and':
                query = query.filter(notes_filter)
            else:  # 'or' is default
                property_filters |= notes_filter
        
        # Apply the combined OR property filters if we're using OR logic and have any property filters
        if search_params['search_operator'] == 'or' and property_filters:
            query = query.filter(property_filters)
        
        # Apply sorting
        if sort_by == 'country':
            order_field = 'headstamp__manufacturer__country__name'
        elif sort_by == 'manufacturer':
            order_field = 'headstamp__manufacturer__code'
        elif sort_by == 'headstamp':
            order_field = 'headstamp__code'
        elif sort_by == 'load_type':
            order_field = 'load_type__display_name'
        elif sort_by == 'cc':
            order_field = 'cc'
        else:
            order_field = 'cart_id'  # Default sort
            
        # Apply sort direction
        if sort_dir == 'desc':
            order_field = f'-{order_field}'
            
        # Order results
        results = query.order_by(order_field)
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'countries': countries,
        'manufacturers': manufacturers,
        'load_types': load_types,
        'bullet_types': bullet_types,
        'case_types': case_types,
        'primer_types': primer_types,
        'pa_colors': pa_colors,
        'search_params': search_params,
        'results': results,
        'performed_search': performed_search,
        'selected_country_name': selected_country_name,
        'selected_manufacturer_name': selected_manufacturer_name,
        'selected_load_type_name': selected_load_type_name,
        'selected_bullet_name': selected_bullet_name,
        'selected_case_type_name': selected_case_type_name,
        'selected_primer_name': selected_primer_name,
        'selected_pa_color_name': selected_pa_color_name,
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
    
    # Get sort parameters
    sort_by = request.GET.get('sort_by', 'code')
    sort_dir = request.GET.get('sort_dir', 'asc')
    
    # Store search parameters
    search_params = {
        'country_id': request.GET.get('country_id', ''),
        'code': request.GET.get('code', ''),
        'code_match_type': request.GET.get('code_match_type', 'contains'),
        'name': request.GET.get('name', ''),
        'name_match_type': request.GET.get('name_match_type', 'contains'),
        'notes': request.GET.get('notes', ''),
        'search_operator': request.GET.get('search_operator', 'or'),
        'sort_by': sort_by,
        'sort_dir': sort_dir,
    }
    
    # Initialize search results and selected country name
    results = None
    selected_country_name = ''
    
    # Determine if search was performed
    performed_search = any(
        v for k, v in search_params.items() 
        if k not in ['code_match_type', 'name_match_type', 'search_operator', 'sort_by', 'sort_dir'] and v
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
        
        # Build property filters based on the search operator (AND or OR)
        from django.db.models import Q
        property_filters = Q()
        
        # Apply code search if provided
        if search_params['code']:
            code = search_params['code']
            code_filter = None
            
            if search_params['code_match_type'] == 'is_exactly':
                # Exact match (case sensitive)
                code_filter = Q(code=code)
            elif search_params['code_match_type'] == 'startswith':
                # Case insensitive starts with
                code_filter = Q(code__istartswith=code)
            else:  # contains (default)
                # Case insensitive contains
                code_filter = Q(code__icontains=code)
            
            if search_params['search_operator'] == 'and':
                query = query.filter(code_filter)
            else:  # 'or' is default
                property_filters |= code_filter
        
        # Apply name search if provided
        if search_params['name']:
            name = search_params['name']
            name_filter = None
            
            if search_params['name_match_type'] == 'startswith':
                # Case insensitive starts with
                name_filter = Q(name__istartswith=name)
            else:  # contains (default)
                # Case insensitive contains
                name_filter = Q(name__icontains=name)
            
            if search_params['search_operator'] == 'and':
                query = query.filter(name_filter)
            else:  # 'or' is default
                property_filters |= name_filter
        
        # Apply notes search (always case insensitive)
        if search_params['notes']:
            notes_filter = Q(note__icontains=search_params['notes'])
            
            if search_params['search_operator'] == 'and':
                query = query.filter(notes_filter)
            else:  # 'or' is default
                property_filters |= notes_filter
        
        # Apply the combined OR property filters if we're using OR logic and have any property filters
        if search_params['search_operator'] == 'or' and property_filters:
            query = query.filter(property_filters)
        
        # Annotate with counts for related items
        from django.db.models import Count
        query = query.annotate(
            headstamp_count=Count('headstamps', distinct=True),
            # Count loads through headstamps
            load_count=Count('headstamps__loads', distinct=True)
        )
        
        # Apply sorting
        if sort_by == 'country':
            order_field = 'country__name'
        elif sort_by == 'name':
            order_field = 'name'
        elif sort_by == 'headstamps':
            order_field = 'headstamp_count'
        elif sort_by == 'loads':
            order_field = 'load_count'
        else:
            order_field = 'code'  # Default sort
            
        # Apply sort direction
        if sort_dir == 'desc':
            order_field = f'-{order_field}'
            
        # Order results
        results = query.order_by(order_field)
        
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
    
    # Get sort parameters
    sort_by = request.GET.get('sort_by', 'code')
    sort_dir = request.GET.get('sort_dir', 'asc')
    
    # Store search parameters
    search_params = {
        'country_id': request.GET.get('country_id', ''),
        'manufacturer_id': request.GET.get('manufacturer_id', ''),
        'headstamp_code': request.GET.get('headstamp_code', ''),
        'headstamp_name': request.GET.get('headstamp_name', ''),
        'code_match_type': request.GET.get('code_match_type', 'contains'),
        'name_match_type': request.GET.get('name_match_type', 'contains'),
        'search_operator': request.GET.get('search_operator', 'or'),
        'notes': request.GET.get('notes', ''),
        'sort_by': sort_by,
        'sort_dir': sort_dir,
    }
    
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
        if k not in ['code_match_type', 'name_match_type', 'search_operator', 'sort_by', 'sort_dir'] and v
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
            
            if search_params['code_match_type'] == 'is_exactly':
                # Case sensitive exact match
                code_filter = Q(code=code)
            elif search_params['code_match_type'] == 'startswith':
                # Case insensitive starts with
                code_filter = Q(code__istartswith=code)
            else:  # contains (default)
                # Case insensitive contains
                code_filter = Q(code__icontains=code)
            
            if search_params['search_operator'] == 'and':
                query = query.filter(code_filter)
            else:  # 'or' is default
                property_filters |= code_filter
        
        # Apply headstamp name search if provided
        if search_params['headstamp_name']:
            name = search_params['headstamp_name']
            name_filter = None
            
            if search_params['name_match_type'] == 'startswith':
                # Case insensitive starts with
                name_filter = Q(name__istartswith=name)
            else:  # contains (default)
                # Case insensitive contains
                name_filter = Q(name__icontains=name)
            
            if search_params['search_operator'] == 'and':
                query = query.filter(name_filter)
            else:  # 'or' is default
                property_filters |= name_filter
        
        # Apply notes search (always case insensitive)
        if search_params['notes']:
            notes_filter = Q(note__icontains=search_params['notes'])
            
            if search_params['search_operator'] == 'and':
                query = query.filter(notes_filter)
            else:  # 'or' is default
                property_filters |= notes_filter
        
        # Apply the combined OR property filters if we're using OR logic and have any property filters
        if search_params['search_operator'] == 'or' and property_filters:
            query = query.filter(property_filters)
        
        # Annotate with count of loads for each headstamp
        from django.db.models import Count
        query = query.annotate(load_count=Count('loads', distinct=True))
        
        # Apply sorting
        if sort_by == 'country':
            order_field = 'manufacturer__country__name'
        elif sort_by == 'manufacturer':
            order_field = 'manufacturer__code'
        elif sort_by == 'name':
            order_field = 'name'
        elif sort_by == 'loads':
            order_field = 'load_count'
        elif sort_by == 'cc':
            order_field = 'cc'
        else:
            order_field = 'code'  # Default sort
            
        # Apply sort direction
        if sort_dir == 'desc':
            order_field = f'-{order_field}'
            
        # Order results
        results = query.order_by(order_field)
    
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

def box_search(request, caliber_code):
    """Advanced search view for boxes."""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get sort parameters
    sort_by = request.GET.get('sort_by', 'bid')
    sort_dir = request.GET.get('sort_dir', 'asc')
    
    # Get available filtering options
    countries = Country.objects.filter(caliber=caliber).order_by('name')
    manufacturers = []
    
    # Get ContentTypes for parent record types
    from django.contrib.contenttypes.models import ContentType
    country_content_type = ContentType.objects.get_for_model(Country)
    manufacturer_content_type = ContentType.objects.get_for_model(Manufacturer)
    headstamp_content_type = ContentType.objects.get_for_model(Headstamp)
    load_content_type = ContentType.objects.get_for_model(Load)
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Parent record type choices for the dropdown
    PARENT_TYPE_CHOICES = [
        ('', 'Any Type'),
        (country_content_type.id, 'Country'),
        (manufacturer_content_type.id, 'Manufacturer'),
        (headstamp_content_type.id, 'Headstamp'),
        (load_content_type.id, 'Load'),
        (date_content_type.id, 'Date'),
        (variation_content_type.id, 'Variation'),
    ]
    
    # Store search parameters
    search_params = {
        'country_id': request.GET.get('country_id', ''),
        'manufacturer_id': request.GET.get('manufacturer_id', ''),
        'headstamp_code': request.GET.get('headstamp_code', ''),
        'headstamp_match_type': request.GET.get('headstamp_match_type', 'contains'),
        'parent_type': request.GET.get('parent_type', ''),
        'location': request.GET.get('location', ''),
        'description': request.GET.get('description', ''),
        'description_match_type': request.GET.get('description_match_type', 'contains'),
        'notes': request.GET.get('notes', ''),
        'search_operator': request.GET.get('search_operator', 'or'),
        'sort_by': sort_by,
        'sort_dir': sort_dir,
    }
    
    # Variables to store selected names for display
    selected_country_name = ''
    selected_manufacturer_name = ''
    selected_parent_type_name = ''
    
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
            
    # If a parent record type is selected, get its name
    if search_params['parent_type']:
        try:
            parent_type_id = int(search_params['parent_type'])
            for ct_id, ct_name in PARENT_TYPE_CHOICES:
                if ct_id and int(ct_id) == parent_type_id:
                    selected_parent_type_name = ct_name
                    break
        except (ValueError, TypeError):
            pass
    
    # Initialize search results
    results = None
    performed_search = any(
        v for k, v in search_params.items() 
        if k not in ['headstamp_match_type', 'description_match_type', 'search_operator', 'sort_by', 'sort_dir'] and v
    )
    
    if performed_search:
        # Get all boxes that belong to this caliber
        # This is complex since boxes can be linked to different levels of the hierarchy
        # First get all relevant entity IDs from each level
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
        variation_ids = list(load_var_ids) + list(date_var_ids)
        
        # Build the base query with all boxes that might belong to this caliber
        from django.db.models import Q
        query = Box.objects.filter(
            Q(content_type=country_content_type, object_id__in=country_ids) |
            Q(content_type=manufacturer_content_type, object_id__in=manufacturer_ids) |
            Q(content_type=headstamp_content_type, object_id__in=headstamp_ids) |
            Q(content_type=load_content_type, object_id__in=load_ids) |
            Q(content_type=date_content_type, object_id__in=date_ids) |
            Q(content_type=variation_content_type, object_id__in=variation_ids)
        ).select_related('content_type')
        
        # Apply parent type filter if provided
        if search_params['parent_type']:
            try:
                parent_type_id = int(search_params['parent_type'])
                query = query.filter(content_type_id=parent_type_id)
            except (ValueError, TypeError):
                pass
                
        # Apply location filter if provided
        if search_params['location']:
            location_filter = Q(location__icontains=search_params['location'])
            
            if search_params['search_operator'] == 'and':
                query = query.filter(location_filter)
            else:  # 'or' is default
                # Store for later OR combination
                location_filter_for_or = location_filter
        else:
            location_filter_for_or = None
                
        # Apply description filter if provided
        if search_params['description']:
            description = search_params['description']
            description_filter = None
            
            if search_params['description_match_type'] == 'startswith':
                description_filter = Q(description__istartswith=description)
            else:  # contains (default)
                description_filter = Q(description__icontains=description)
                
            if search_params['search_operator'] == 'and':
                query = query.filter(description_filter)
            else:  # 'or' is default
                # Store for later OR combination
                description_filter_for_or = description_filter
        else:
            description_filter_for_or = None
            
        # Apply notes filter if provided
        if search_params['notes']:
            notes_filter = Q(note__icontains=search_params['notes'])
            
            if search_params['search_operator'] == 'and':
                query = query.filter(notes_filter)
            else:  # 'or' is default
                # Store for later OR combination
                notes_filter_for_or = notes_filter
        else:
            notes_filter_for_or = None
            
        # Now we need to filter based on the other parameters (country, manufacturer, headstamp)
        # This is complex because we need to filter through the parent relationships
        
        # For country filter
        if search_params['country_id']:
            try:
                country_id = int(search_params['country_id'])
                
                # Direct country boxes
                country_boxes = Q(content_type=country_content_type, object_id=country_id)
                
                # Manufacturer boxes under this country
                manufacturer_boxes = Q(
                    content_type=manufacturer_content_type,
                    object_id__in=Manufacturer.objects.filter(country_id=country_id).values_list('id', flat=True)
                )
                
                # Headstamp boxes under manufacturers in this country
                headstamp_boxes = Q(
                    content_type=headstamp_content_type,
                    object_id__in=Headstamp.objects.filter(manufacturer__country_id=country_id).values_list('id', flat=True)
                )
                
                # Load boxes under headstamps in this country
                load_boxes = Q(
                    content_type=load_content_type,
                    object_id__in=Load.objects.filter(headstamp__manufacturer__country_id=country_id).values_list('id', flat=True)
                )
                
                # Date boxes under loads in this country
                date_boxes = Q(
                    content_type=date_content_type,
                    object_id__in=Date.objects.filter(load__headstamp__manufacturer__country_id=country_id).values_list('id', flat=True)
                )
                
                # Variation boxes under loads or dates in this country
                variation_boxes = Q(
                    content_type=variation_content_type,
                    object_id__in=Variation.objects.filter(
                        Q(load__headstamp__manufacturer__country_id=country_id) |
                        Q(date__load__headstamp__manufacturer__country_id=country_id)
                    ).values_list('id', flat=True)
                )
                
                country_filter = country_boxes | manufacturer_boxes | headstamp_boxes | load_boxes | date_boxes | variation_boxes
                
                if search_params['search_operator'] == 'and':
                    query = query.filter(country_filter)
                else:  # 'or' is default
                    # Store for later OR combination
                    country_filter_for_or = country_filter
            except (ValueError, TypeError):
                country_filter_for_or = None
        else:
            country_filter_for_or = None
            
        # For manufacturer filter
        if search_params['manufacturer_id']:
            try:
                manufacturer_id = int(search_params['manufacturer_id'])
                
                # Direct manufacturer boxes
                manufacturer_boxes = Q(content_type=manufacturer_content_type, object_id=manufacturer_id)
                
                # Headstamp boxes under this manufacturer
                headstamp_boxes = Q(
                    content_type=headstamp_content_type,
                    object_id__in=Headstamp.objects.filter(manufacturer_id=manufacturer_id).values_list('id', flat=True)
                )
                
                # Load boxes under headstamps from this manufacturer
                load_boxes = Q(
                    content_type=load_content_type,
                    object_id__in=Load.objects.filter(headstamp__manufacturer_id=manufacturer_id).values_list('id', flat=True)
                )
                
                # Date boxes under loads from this manufacturer
                date_boxes = Q(
                    content_type=date_content_type,
                    object_id__in=Date.objects.filter(load__headstamp__manufacturer_id=manufacturer_id).values_list('id', flat=True)
                )
                
                # Variation boxes under loads or dates from this manufacturer
                variation_boxes = Q(
                    content_type=variation_content_type,
                    object_id__in=Variation.objects.filter(
                        Q(load__headstamp__manufacturer_id=manufacturer_id) |
                        Q(date__load__headstamp__manufacturer_id=manufacturer_id)
                    ).values_list('id', flat=True)
                )
                
                manufacturer_filter = manufacturer_boxes | headstamp_boxes | load_boxes | date_boxes | variation_boxes
                
                if search_params['search_operator'] == 'and':
                    query = query.filter(manufacturer_filter)
                else:  # 'or' is default
                    # Store for later OR combination
                    manufacturer_filter_for_or = manufacturer_filter
            except (ValueError, TypeError):
                manufacturer_filter_for_or = None
        else:
            manufacturer_filter_for_or = None
            
        # For headstamp code filter
        if search_params['headstamp_code']:
            headstamp_code = search_params['headstamp_code']
            
            # Build the appropriate headstamp filter based on the match type
            if search_params['headstamp_match_type'] == 'is_exactly':
                headstamp_base_filter = Q(code=headstamp_code)
            elif search_params['headstamp_match_type'] == 'startswith':
                headstamp_base_filter = Q(code__istartswith=headstamp_code)
            else:  # contains
                headstamp_base_filter = Q(code__icontains=headstamp_code)
                
            # Get headstamps that match the filter
            matching_headstamps = Headstamp.objects.filter(
                headstamp_base_filter,
                manufacturer__country__caliber=caliber
            )
            
            # Direct headstamp boxes
            headstamp_boxes = Q(
                content_type=headstamp_content_type,
                object_id__in=matching_headstamps.values_list('id', flat=True)
            )
            
            # Load boxes under matching headstamps
            load_boxes = Q(
                content_type=load_content_type,
                object_id__in=Load.objects.filter(headstamp__in=matching_headstamps).values_list('id', flat=True)
            )
            
            # Date boxes under loads with matching headstamps
            date_boxes = Q(
                content_type=date_content_type,
                object_id__in=Date.objects.filter(load__headstamp__in=matching_headstamps).values_list('id', flat=True)
            )
            
            # Variation boxes under loads or dates with matching headstamps
            variation_boxes = Q(
                content_type=variation_content_type,
                object_id__in=Variation.objects.filter(
                    Q(load__headstamp__in=matching_headstamps) |
                    Q(date__load__headstamp__in=matching_headstamps)
                ).values_list('id', flat=True)
            )
            
            headstamp_filter = headstamp_boxes | load_boxes | date_boxes | variation_boxes
            
            if search_params['search_operator'] == 'and':
                query = query.filter(headstamp_filter)
            else:  # 'or' is default
                # Store for later OR combination
                headstamp_filter_for_or = headstamp_filter
        else:
            headstamp_filter_for_or = None
            
        # Apply the combined OR filters if we're using OR logic
        if search_params['search_operator'] == 'or':
            combined_or_filter = Q()
            
            # Add each filter that was specified
            for filter_item in [
                country_filter_for_or, manufacturer_filter_for_or, headstamp_filter_for_or,
                location_filter_for_or, description_filter_for_or, notes_filter_for_or
            ]:
                if filter_item is not None:
                    combined_or_filter |= filter_item
                    
            # Apply the combined OR filter if any filters were specified
            if combined_or_filter != Q():
                query = query.filter(combined_or_filter)
                
        # Apply sorting
        if sort_by == 'parent_type':
            order_field = 'content_type__model'
        elif sort_by == 'parent':
            order_field = 'object_id'  # Limited but better than nothing
        elif sort_by == 'location':
            order_field = 'location'
        elif sort_by == 'description':
            order_field = 'description'
        elif sort_by == 'cc':
            order_field = 'cc'
        else:
            order_field = 'bid'  # Default sort
            
        # Apply sort direction
        if sort_dir == 'desc':
            order_field = f'-{order_field}'
            
        # Order results
        results = query.order_by(order_field).distinct()
        
        # Annotate with parent display names (this has to be done in Python since it spans different models)
        for box in results:
            # Get parent object and set the display field
            try:
                parent_model = box.content_type.model_class()
                parent_obj = parent_model.objects.get(pk=box.object_id)
                
                # Set parent display name based on the type of parent
                if hasattr(parent_obj, 'cart_id'):
                    box.parent_display = parent_obj.cart_id
                elif hasattr(parent_obj, 'bid'):
                    box.parent_display = parent_obj.bid
                elif hasattr(parent_obj, 'name'):
                    box.parent_display = parent_obj.name
                elif hasattr(parent_obj, 'code'):
                    box.parent_display = parent_obj.code
                else:
                    box.parent_display = f"ID: {parent_obj.pk}"
                    
                # Set parent type display name
                box.parent_type_display = box.content_type.model
                
            except (AttributeError, parent_model.DoesNotExist):
                box.parent_display = f"Unknown ({box.object_id})"
                box.parent_type_display = "Unknown"
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'countries': countries,
        'manufacturers': manufacturers,
        'parent_type_choices': PARENT_TYPE_CHOICES,
        'search_params': search_params,
        'results': results,
        'performed_search': performed_search,
        'selected_country_name': selected_country_name,
        'selected_manufacturer_name': selected_manufacturer_name,
        'selected_parent_type_name': selected_parent_type_name,
    }
    
    return render(request, 'collection/box_search.html', context)