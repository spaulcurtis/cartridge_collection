from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box
from ..forms.country_forms import CountryForm
from ..utils.note_utils import process_notes

def country_detail(request, caliber_code, country_id):
    """View for showing details of a specific country"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get the country
    country = get_object_or_404(Country, id=country_id, caliber=caliber)
    
    # Process notes
    from ..utils.note_utils import process_notes
    country_notes = process_notes(country.note)
    country.note_has_notes = country_notes['has_notes']
    country.note_public_notes = country_notes['public_notes']
    country.note_confidential_notes = country_notes['confidential_notes']
    country.note_has_confidential = country_notes['has_confidential']
    
    # Get ContentType IDs for box queries - we'll need these for several operations
    from django.contrib.contenttypes.models import ContentType
    country_content_type = ContentType.objects.get_for_model(Country)
    manufacturer_content_type = ContentType.objects.get_for_model(Manufacturer)
    headstamp_content_type = ContentType.objects.get_for_model(Headstamp)
    load_content_type = ContentType.objects.get_for_model(Load)
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get manufacturers for this country
    manufacturers = Manufacturer.objects.filter(country=country).order_by('code')
    
    # Create a mapping of manufacturer_id to manufacturer objects for easy reference
    manufacturer_dict = {manufacturer.id: manufacturer for manufacturer in manufacturers}
    
    # For each manufacturer, gather the related IDs at various levels
    manufacturer_related_ids = {}
    
    # Headstamp IDs per manufacturer
    headstamp_query = Headstamp.objects.filter(
        manufacturer__in=manufacturers
    ).values('manufacturer_id', 'id', 'image')
    
    for item in headstamp_query:
        manufacturer_id = item['manufacturer_id']
        headstamp_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if manufacturer_id not in manufacturer_related_ids:
            manufacturer_related_ids[manufacturer_id] = {
                'headstamp_ids': [],
                'load_ids': [],
                'date_ids': [],
                'load_var_ids': [],
                'date_var_ids': []
            }
            
        manufacturer_related_ids[manufacturer_id]['headstamp_ids'].append(headstamp_id)
        
        # Count headstamps
        if not hasattr(manufacturer_dict[manufacturer_id], 'headstamp_count'):
            manufacturer_dict[manufacturer_id].headstamp_count = 0
            manufacturer_dict[manufacturer_id].headstamp_image_count = 0
            
        manufacturer_dict[manufacturer_id].headstamp_count += 1
        if has_image:
            manufacturer_dict[manufacturer_id].headstamp_image_count += 1
    
    # Load IDs per manufacturer
    load_query = Load.objects.filter(
        headstamp__manufacturer__in=manufacturers
    ).values('headstamp__manufacturer_id', 'id', 'image')
    
    for item in load_query:
        manufacturer_id = item['headstamp__manufacturer_id']
        load_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if manufacturer_id not in manufacturer_related_ids:
            continue
            
        manufacturer_related_ids[manufacturer_id]['load_ids'].append(load_id)
        
        # Count loads
        if not hasattr(manufacturer_dict[manufacturer_id], 'load_count'):
            manufacturer_dict[manufacturer_id].load_count = 0
            manufacturer_dict[manufacturer_id].load_image_count = 0
            
        manufacturer_dict[manufacturer_id].load_count += 1
        if has_image:
            manufacturer_dict[manufacturer_id].load_image_count += 1
    
    # Date IDs per manufacturer
    date_query = Date.objects.filter(
        load__headstamp__manufacturer__in=manufacturers
    ).values('load__headstamp__manufacturer_id', 'id', 'image')
    
    for item in date_query:
        manufacturer_id = item['load__headstamp__manufacturer_id']
        date_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if manufacturer_id not in manufacturer_related_ids:
            continue
            
        manufacturer_related_ids[manufacturer_id]['date_ids'].append(date_id)
        
        # Count dates
        if not hasattr(manufacturer_dict[manufacturer_id], 'date_count'):
            manufacturer_dict[manufacturer_id].date_count = 0
            manufacturer_dict[manufacturer_id].date_image_count = 0
            
        manufacturer_dict[manufacturer_id].date_count += 1
        if has_image:
            manufacturer_dict[manufacturer_id].date_image_count += 1
    
    # Load Variation IDs per manufacturer
    load_var_query = Variation.objects.filter(
        load__headstamp__manufacturer__in=manufacturers,
        load__isnull=False
    ).values('load__headstamp__manufacturer_id', 'id', 'image')
    
    for item in load_var_query:
        manufacturer_id = item['load__headstamp__manufacturer_id']
        var_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if manufacturer_id not in manufacturer_related_ids:
            continue
            
        manufacturer_related_ids[manufacturer_id]['load_var_ids'].append(var_id)
        
        # Count load variations
        if not hasattr(manufacturer_dict[manufacturer_id], 'var_count'):
            manufacturer_dict[manufacturer_id].var_count = 0
            manufacturer_dict[manufacturer_id].var_image_count = 0
            
        manufacturer_dict[manufacturer_id].var_count += 1
        if has_image:
            manufacturer_dict[manufacturer_id].var_image_count += 1
    
    # Date Variation IDs per manufacturer
    date_var_query = Variation.objects.filter(
        date__load__headstamp__manufacturer__in=manufacturers,
        date__isnull=False
    ).values('date__load__headstamp__manufacturer_id', 'id', 'image')
    
    for item in date_var_query:
        manufacturer_id = item['date__load__headstamp__manufacturer_id']
        var_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if manufacturer_id not in manufacturer_related_ids:
            continue
            
        manufacturer_related_ids[manufacturer_id]['date_var_ids'].append(var_id)
        
        # Count date variations
        if not hasattr(manufacturer_dict[manufacturer_id], 'date_var_count'):
            manufacturer_dict[manufacturer_id].date_var_count = 0
            manufacturer_dict[manufacturer_id].date_var_image_count = 0
            
        manufacturer_dict[manufacturer_id].date_var_count += 1
        if has_image:
            manufacturer_dict[manufacturer_id].date_var_image_count += 1
    
    # Initialize box counts for manufacturers
    for manufacturer in manufacturers:
        manufacturer.box_count = 0
        manufacturer.box_image_count = 0
    
    # Count boxes at each level and add to appropriate manufacturer
    # Manufacturer-level boxes
    manufacturer_box_counts = Box.objects.filter(
        content_type=manufacturer_content_type,
        object_id__in=[m.id for m in manufacturers]
    ).values('object_id').annotate(
        box_count=Count('id'),
        image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
    )
    
    for item in manufacturer_box_counts:
        manufacturer_id = item['object_id']
        box_count = item['box_count']
        image_count = item['image_count']
        
        if manufacturer_id in manufacturer_dict:
            manufacturer_dict[manufacturer_id].box_count += box_count
            manufacturer_dict[manufacturer_id].box_image_count += image_count
    
    # Headstamp-level boxes
    for manufacturer_id, ids in manufacturer_related_ids.items():
        headstamp_ids = ids.get('headstamp_ids', [])
        if not headstamp_ids:
            continue
            
        headstamp_box_counts = Box.objects.filter(
            content_type=headstamp_content_type,
            object_id__in=headstamp_ids
        ).aggregate(
            box_count=Count('id'),
            image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
        )
        
        manufacturer_dict[manufacturer_id].box_count += headstamp_box_counts['box_count'] or 0
        manufacturer_dict[manufacturer_id].box_image_count += headstamp_box_counts['image_count'] or 0
    
    # Load-level boxes
    for manufacturer_id, ids in manufacturer_related_ids.items():
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
        
        manufacturer_dict[manufacturer_id].box_count += load_box_counts['box_count'] or 0
        manufacturer_dict[manufacturer_id].box_image_count += load_box_counts['image_count'] or 0
    
    # Date-level boxes
    for manufacturer_id, ids in manufacturer_related_ids.items():
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
        
        manufacturer_dict[manufacturer_id].box_count += date_box_counts['box_count'] or 0
        manufacturer_dict[manufacturer_id].box_image_count += date_box_counts['image_count'] or 0
    
    # Load Variation-level boxes
    for manufacturer_id, ids in manufacturer_related_ids.items():
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
        
        manufacturer_dict[manufacturer_id].box_count += load_var_box_counts['box_count'] or 0
        manufacturer_dict[manufacturer_id].box_image_count += load_var_box_counts['image_count'] or 0
    
    # Date Variation-level boxes
    for manufacturer_id, ids in manufacturer_related_ids.items():
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
        
        manufacturer_dict[manufacturer_id].box_count += date_var_box_counts['box_count'] or 0
        manufacturer_dict[manufacturer_id].box_image_count += date_var_box_counts['image_count'] or 0
    
    # Initialize counts for manufacturers without data
    for manufacturer in manufacturers:
        if not hasattr(manufacturer, 'headstamp_count'):
            manufacturer.headstamp_count = 0
            manufacturer.headstamp_image_count = 0
        if not hasattr(manufacturer, 'load_count'):
            manufacturer.load_count = 0
            manufacturer.load_image_count = 0
        if not hasattr(manufacturer, 'date_count'):
            manufacturer.date_count = 0
            manufacturer.date_image_count = 0
        if not hasattr(manufacturer, 'var_count'):
            manufacturer.var_count = 0
            manufacturer.var_image_count = 0
        if not hasattr(manufacturer, 'date_var_count'):
            manufacturer.date_var_count = 0
            manufacturer.date_var_image_count = 0
    
    # Get boxes directly associated with this country
    direct_boxes = Box.objects.filter(
        content_type=country_content_type,
        object_id=country.pk
    ).order_by('bid')
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'country': country,
        'manufacturers': manufacturers,
        'direct_boxes': direct_boxes,
        'country_content_type': country_content_type,
    }
    
    return render(request, 'collection/country_detail.html', context)


def country_list(request, caliber_code):
    """
    View for listing countries in a caliber with dynamic counts.
    Uses optimized Django ORM queries for the complex hierarchical counting.
    """
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)

    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')

    # Get ContentType IDs for box queries - we'll need these for several operations
    country_content_type = ContentType.objects.get_for_model(Country)
    manufacturer_content_type = ContentType.objects.get_for_model(Manufacturer)
    headstamp_content_type = ContentType.objects.get_for_model(Headstamp)
    load_content_type = ContentType.objects.get_for_model(Load)
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get all countries for this caliber
    countries = Country.objects.filter(caliber=caliber).order_by('name')
    
    # Create a mapping of country_id to country objects for easy reference
    country_dict = {country.id: country for country in countries}
    
    # For each country, gather the related IDs at various levels
    country_related_ids = {}
    
    # Manufacturer IDs per country
    manufacturer_query = Manufacturer.objects.filter(
        country__caliber=caliber
    ).values('country_id', 'id')
    
    for item in manufacturer_query:
        country_id = item['country_id']
        manufacturer_id = item['id']
        
        if country_id not in country_related_ids:
            country_related_ids[country_id] = {
                'manufacturer_ids': [],
                'headstamp_ids': [],
                'load_ids': [],
                'date_ids': [],
                'load_var_ids': [],
                'date_var_ids': []
            }
        
        country_related_ids[country_id]['manufacturer_ids'].append(manufacturer_id)
    
    # Headstamp IDs per country
    headstamp_query = Headstamp.objects.filter(
        manufacturer__country__caliber=caliber
    ).values('manufacturer__country_id', 'id', 'image')
    
    for item in headstamp_query:
        country_id = item['manufacturer__country_id']
        headstamp_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if country_id not in country_related_ids:
            continue
            
        country_related_ids[country_id]['headstamp_ids'].append(headstamp_id)
        
        # Count headstamps
        if not hasattr(country_dict[country_id], 'headstamp_count'):
            country_dict[country_id].headstamp_count = 0
            country_dict[country_id].headstamp_image_count = 0
            
        country_dict[country_id].headstamp_count += 1
        if has_image:
            country_dict[country_id].headstamp_image_count += 1
    
    # Load IDs per country
    load_query = Load.objects.filter(
        headstamp__manufacturer__country__caliber=caliber
    ).values('headstamp__manufacturer__country_id', 'id', 'image')
    
    for item in load_query:
        country_id = item['headstamp__manufacturer__country_id']
        load_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if country_id not in country_related_ids:
            continue
            
        country_related_ids[country_id]['load_ids'].append(load_id)
        
        # Count loads
        if not hasattr(country_dict[country_id], 'load_count'):
            country_dict[country_id].load_count = 0
            country_dict[country_id].load_image_count = 0
            
        country_dict[country_id].load_count += 1
        if has_image:
            country_dict[country_id].load_image_count += 1
    
    # Date IDs per country
    date_query = Date.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber
    ).values('load__headstamp__manufacturer__country_id', 'id', 'image')
    
    for item in date_query:
        country_id = item['load__headstamp__manufacturer__country_id']
        date_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if country_id not in country_related_ids:
            continue
            
        country_related_ids[country_id]['date_ids'].append(date_id)
        
        # Count dates
        if not hasattr(country_dict[country_id], 'date_count'):
            country_dict[country_id].date_count = 0
            country_dict[country_id].date_image_count = 0
            
        country_dict[country_id].date_count += 1
        if has_image:
            country_dict[country_id].date_image_count += 1
    
    # Load Variation IDs per country
    load_var_query = Variation.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber,
        load__isnull=False
    ).values('load__headstamp__manufacturer__country_id', 'id', 'image')
    
    for item in load_var_query:
        country_id = item['load__headstamp__manufacturer__country_id']
        var_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if country_id not in country_related_ids:
            continue
            
        country_related_ids[country_id]['load_var_ids'].append(var_id)
        
        # Count load variations
        if not hasattr(country_dict[country_id], 'var_count'):
            country_dict[country_id].var_count = 0
            country_dict[country_id].var_image_count = 0
            
        country_dict[country_id].var_count += 1
        if has_image:
            country_dict[country_id].var_image_count += 1
    
    # Date Variation IDs per country
    date_var_query = Variation.objects.filter(
        date__load__headstamp__manufacturer__country__caliber=caliber,
        date__isnull=False
    ).values('date__load__headstamp__manufacturer__country_id', 'id', 'image')
    
    for item in date_var_query:
        country_id = item['date__load__headstamp__manufacturer__country_id']
        var_id = item['id']
        has_image = item['image'] and item['image'] != ''
        
        if country_id not in country_related_ids:
            continue
            
        country_related_ids[country_id]['date_var_ids'].append(var_id)
        
        # Count date variations
        if not hasattr(country_dict[country_id], 'date_var_count'):
            country_dict[country_id].date_var_count = 0
            country_dict[country_id].date_var_image_count = 0
            
        country_dict[country_id].date_var_count += 1
        if has_image:
            country_dict[country_id].date_var_image_count += 1
    
    # Count manufacturers
    manufacturer_counts = Manufacturer.objects.filter(
        country__caliber=caliber
    ).values('country_id').annotate(count=Count('id'))
    
    for item in manufacturer_counts:
        country_id = item['country_id']
        count = item['count']
        
        if country_id in country_dict:
            country_dict[country_id].manuf_count = count
    
    # Initialize counts for countries without data
    for country in countries:
        if not hasattr(country, 'manuf_count'):
            country.manuf_count = 0
        if not hasattr(country, 'headstamp_count'):
            country.headstamp_count = 0
            country.headstamp_image_count = 0
        if not hasattr(country, 'load_count'):
            country.load_count = 0
            country.load_image_count = 0
        if not hasattr(country, 'date_count'):
            country.date_count = 0
            country.date_image_count = 0
        if not hasattr(country, 'var_count'):
            country.var_count = 0
            country.var_image_count = 0
        if not hasattr(country, 'date_var_count'):
            country.date_var_count = 0
            country.date_var_image_count = 0
        
        # Initialize box counts
        country.box_count = 0
        country.box_image_count = 0
    
    # Count boxes at each level and add to appropriate country
    # Country-level boxes
    country_box_counts = Box.objects.filter(
        content_type=country_content_type,
        object_id__in=[c.id for c in countries]
    ).values('object_id').annotate(
        box_count=Count('id'),
        image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
    )
    
    for item in country_box_counts:
        country_id = item['object_id']
        box_count = item['box_count']
        image_count = item['image_count']
        
        if country_id in country_dict:
            country_dict[country_id].box_count += box_count
            country_dict[country_id].box_image_count += image_count
    
    # Manufacturer-level boxes
    for country_id, ids in country_related_ids.items():
        manufacturer_ids = ids.get('manufacturer_ids', [])
        if not manufacturer_ids:
            continue
            
        manufacturer_box_counts = Box.objects.filter(
            content_type=manufacturer_content_type,
            object_id__in=manufacturer_ids
        ).aggregate(
            box_count=Count('id'),
            image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
        )
        
        country_dict[country_id].box_count += manufacturer_box_counts['box_count'] or 0
        country_dict[country_id].box_image_count += manufacturer_box_counts['image_count'] or 0
    
    # Headstamp-level boxes
    for country_id, ids in country_related_ids.items():
        headstamp_ids = ids.get('headstamp_ids', [])
        if not headstamp_ids:
            continue
            
        headstamp_box_counts = Box.objects.filter(
            content_type=headstamp_content_type,
            object_id__in=headstamp_ids
        ).aggregate(
            box_count=Count('id'),
            image_count=Count('id', filter=Q(image__isnull=False) & ~Q(image=''))
        )
        
        country_dict[country_id].box_count += headstamp_box_counts['box_count'] or 0
        country_dict[country_id].box_image_count += headstamp_box_counts['image_count'] or 0
    
    # Load-level boxes
    for country_id, ids in country_related_ids.items():
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
        
        country_dict[country_id].box_count += load_box_counts['box_count'] or 0
        country_dict[country_id].box_image_count += load_box_counts['image_count'] or 0
    
    # Date-level boxes
    for country_id, ids in country_related_ids.items():
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
        
        country_dict[country_id].box_count += date_box_counts['box_count'] or 0
        country_dict[country_id].box_image_count += date_box_counts['image_count'] or 0
    
    # Load Variation-level boxes
    for country_id, ids in country_related_ids.items():
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
        
        country_dict[country_id].box_count += load_var_box_counts['box_count'] or 0
        country_dict[country_id].box_image_count += load_var_box_counts['image_count'] or 0
    
    # Date Variation-level boxes
    for country_id, ids in country_related_ids.items():
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
        
        country_dict[country_id].box_count += date_var_box_counts['box_count'] or 0
        country_dict[country_id].box_image_count += date_var_box_counts['image_count'] or 0

    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'countries': countries,
    }

    return render(request, 'collection/country_list.html', context)

@login_required
@permission_required('collection.add_country', raise_exception=True)
def country_create(request, caliber_code):
    """View for creating a new country"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    if request.method == 'POST':
        form = CountryForm(request.POST)
        if form.is_valid():
            country = form.save(commit=False)
            country.caliber = caliber
            country.save()
            messages.success(request, f"Country '{country.name}' was created successfully.")
            return redirect('country_detail', caliber_code=caliber_code, country_id=country.id)
    else:
        form = CountryForm()
    
    return render(request, 'collection/country_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'title': 'Add New Country',
        'submit_text': 'Create Country',
    })

@login_required
@permission_required('collection.change_country', raise_exception=True)
def country_update(request, caliber_code, country_id):
    """View for updating a country"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    country = get_object_or_404(Country, id=country_id, caliber=caliber)
    
    if request.method == 'POST':
        form = CountryForm(request.POST, instance=country)
        if form.is_valid():
            form.save()
            messages.success(request, f"Country '{country.name}' was updated successfully.")
            return redirect('country_detail', caliber_code=caliber_code, country_id=country.id)
    else:
        form = CountryForm(instance=country)
    
    return render(request, 'collection/country_form.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'form': form,
        'country': country,
        'title': f'Edit Country: {country.name}',
        'submit_text': 'Update Country',
    })

@login_required
@permission_required('collection.delete_country', raise_exception=True)
def country_delete(request, caliber_code, country_id):
    """View for deleting a country"""
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    country = get_object_or_404(Country, id=country_id, caliber=caliber)
    
    # Check if there are any dependent manufacturers - we'll check this regardless of request method
    has_manufacturers = Manufacturer.objects.filter(country=country).exists()
    has_boxes = False
    
    # Check if there are any direct boxes attached
    country_content_type = ContentType.objects.get_for_model(Country)
    has_boxes = Box.objects.filter(content_type=country_content_type, object_id=country.pk).exists()
    
    # Process notes for display in the template
    processed_notes = process_notes(country.note)
    
    if request.method == 'POST':
        if has_manufacturers:
            messages.error(request, f"Cannot delete '{country.name}' because it has manufacturers associated with it. Remove the manufacturers first.")
            return redirect('country_detail', caliber_code=caliber_code, country_id=country.id)
        
        if has_boxes:
            messages.error(request, f"Cannot delete '{country.name}' because it has boxes directly associated with it. Remove the boxes first.")
            return redirect('country_detail', caliber_code=caliber_code, country_id=country.id)
            
        country_name = country.name
        country.delete()
        messages.success(request, f"Country '{country_name}' was deleted successfully.")
        return redirect('country_list', caliber_code=caliber_code)
    
    return render(request, 'collection/country_confirm_delete.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'country': country,
        'title': f'Delete Country: {country.name}',
        'has_manufacturers': has_manufacturers,
        'has_boxes': has_boxes,
        'can_delete': not has_manufacturers and not has_boxes,
        'country_notes': processed_notes,
    })
