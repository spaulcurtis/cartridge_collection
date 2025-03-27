from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Prefetch, Q
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from ..models import Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box

# def country_list(request, caliber_code):
#     """View for listing countries in a caliber"""
#     # Get the current caliber
#     caliber = get_object_or_404(Caliber, code=caliber_code)
    
#     # Get all calibers for the dropdown
#     all_calibers = Caliber.objects.all().order_by('order', 'name')
    
#     # Get countries for this caliber with prefetched manufacturers
#     countries = Country.objects.filter(caliber=caliber).prefetch_related(
#         'manufacturer_set'
#     ).order_by('name')
    
#     # For now, let's use a simpler approach for counts that's reasonably efficient
#     for country in countries:
#         # Count of manufacturers
#         country.manuf_count = country.manufacturer_set.count()
        
#         # Initialize counters
#         country.headstamp_count = 0
#         country.load_count = 0
#         country.date_count = 0
#         country.var_count = 0
#         country.date_var_count = 0
        
#         for manuf in country.manufacturer_set.all():
#             # Get headstamp count for this manufacturer
#             hs_count = Headstamp.objects.filter(manufacturer=manuf).count()
#             country.headstamp_count += hs_count
            
#             # Get counts for loads, dates, and variations
#             headstamps = Headstamp.objects.filter(manufacturer=manuf)
#             for hs in headstamps:
#                 loads = Load.objects.filter(headstamp=hs)
#                 country.load_count += loads.count()
                
#                 for load in loads:
#                     country.date_count += Date.objects.filter(load=load).count()
#                     country.var_count += Variation.objects.filter(load=load).count()
                    
#                     # Date variations
#                     dates = Date.objects.filter(load=load)
#                     for date in dates:
#                         country.date_var_count += Variation.objects.filter(date=date).count()
        
#         # Get box count using the method in the Country model
#         country.box_count = country.total_box_count()
    
#     context = {
#         'caliber': caliber,
#         'all_calibers': all_calibers,
#         'countries': countries,
#     }
    
#     return render(request, 'collection/country_list.html', context)

def country_detail(request, caliber_code, country_id):
    """View for showing details of a specific country"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get the country
    country = get_object_or_404(Country, id=country_id, caliber=caliber)
    
    # Get manufacturers for this country
    manufacturers = Manufacturer.objects.filter(country=country).order_by('code')
    
    # Add counts as attributes for each manufacturer
    for manuf in manufacturers:
        # Count of headstamps
        manuf.headstamp_count = manuf.headstamps.count()
        
        # Initialize counters
        manuf.load_count = 0
        manuf.date_count = 0
        manuf.var_count = 0
        manuf.date_var_count = 0
        
        # Get loads, dates, and variations
        for hs in manuf.headstamps.all():
            loads = Load.objects.filter(headstamp=hs)
            manuf.load_count += loads.count()
            
            for load in loads:
                dates = Date.objects.filter(load=load)
                manuf.date_count += dates.count()
                manuf.var_count += Variation.objects.filter(load=load).count()
                
                # Date variations
                for date in dates:
                    manuf.date_var_count += Variation.objects.filter(date=date).count()
        
        # Get box count 
        manuf.box_count = manuf.total_box_count()
    
    # Get boxes directly associated with this country
    country_content_type = ContentType.objects.get_for_model(Country)
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
    }
    
    return render(request, 'collection/country_detail.html', context)

def country_list(request, caliber_code):
    """View for listing countries in a caliber"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get countries for this caliber - no calculations, just the countries
    countries = Country.objects.filter(caliber=caliber).order_by('name')
    
    # Add dummy counts (both item counts and image counts)
    for country in countries:
        # Record counts
        country.manuf_count = 12
        country.headstamp_count = 45
        country.load_count = 78
        country.date_count = 23
        country.var_count = 9
        country.date_var_count = 4
        country.box_count = 15
        
        # Image counts
        country.headstamp_image_count = 25
        country.load_image_count = 42
        country.date_image_count = 11
        country.var_image_count = 5
        country.date_var_image_count = 2
        country.box_image_count = 8
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'countries': countries,
    }
    
    return render(request, 'collection/country_list.html', context)


def country_create(request, caliber_code):
    """View for creating a new country"""
    # This is a placeholder - we'll implement the actual form processing later
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber, 
        'all_calibers': all_calibers,
        'title': 'Add New Country',
        'message': 'Country creation form is under construction'
    })

def country_update(request, caliber_code, country_id):
    """View for updating a country"""
    # This is a placeholder - we'll implement the actual form processing later
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    country = get_object_or_404(Country, id=country_id, caliber=caliber)
    
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'title': f'Edit Country: {country.name}',
        'message': 'Country edit form is under construction'
    })

def country_delete(request, caliber_code, country_id):
    """View for deleting a country"""
    # This is a placeholder - we'll implement the actual deletion logic later
    caliber = get_object_or_404(Caliber, code=caliber_code)
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    country = get_object_or_404(Country, id=country_id, caliber=caliber)
    
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'title': f'Delete Country: {country.name}',
        'message': 'Country deletion confirmation is under construction'
    })
