from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Prefetch, Sum, F, Value, IntegerField, Case, When, Subquery, OuterRef
from django.db.models.functions import Upper, Substr
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.decorators.cache import cache_control

import os
import logging
import mimetypes
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.views.decorators.cache import cache_control

from ..models import Caliber, Country, Manufacturer, Headstamp, Load, LoadType, Date, Variation, Box, CollectionInfo

def landing(request):
    """Landing page with caliber selection"""
    # Get all calibers
    calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Get ContentType objects once outside the loop
    country_ct = ContentType.objects.get_for_model(Country)
    manufacturer_ct = ContentType.objects.get_for_model(Manufacturer)
    headstamp_ct = ContentType.objects.get_for_model(Headstamp)
    load_ct = ContentType.objects.get_for_model(Load)
    date_ct = ContentType.objects.get_for_model(Date)
    variation_ct = ContentType.objects.get_for_model(Variation)
    
    # Calculate actual artifact counts for each caliber
    for caliber in calibers:
        # Count loads, dates, and variations
        load_count = Load.objects.filter(headstamp__manufacturer__country__caliber=caliber).count()
        date_count = Date.objects.filter(load__headstamp__manufacturer__country__caliber=caliber).count()
        variation_count = Variation.objects.filter(
            Q(load__headstamp__manufacturer__country__caliber=caliber) |
            Q(date__load__headstamp__manufacturer__country__caliber=caliber)
        ).count()
        
        # Get IDs for box query
        country_ids = Country.objects.filter(caliber=caliber).values_list('id', flat=True)
        manufacturer_ids = Manufacturer.objects.filter(country__caliber=caliber).values_list('id', flat=True)
        headstamp_ids = Headstamp.objects.filter(manufacturer__country__caliber=caliber).values_list('id', flat=True)
        load_ids = Load.objects.filter(headstamp__manufacturer__country__caliber=caliber).values_list('id', flat=True)
        date_ids = Date.objects.filter(load__headstamp__manufacturer__country__caliber=caliber).values_list('id', flat=True)
        variation_ids = Variation.objects.filter(
            Q(load__headstamp__manufacturer__country__caliber=caliber) |
            Q(date__load__headstamp__manufacturer__country__caliber=caliber)
        ).values_list('id', flat=True)
        
        # Count boxes at all levels
        box_count = Box.objects.filter(
            Q(content_type=country_ct, object_id__in=country_ids) |
            Q(content_type=manufacturer_ct, object_id__in=manufacturer_ids) |
            Q(content_type=headstamp_ct, object_id__in=headstamp_ids) |
            Q(content_type=load_ct, object_id__in=load_ids) |
            Q(content_type=date_ct, object_id__in=date_ids) |
            Q(content_type=variation_ct, object_id__in=variation_ids)
        ).count()
        
        # Set the calculated total artifact count
        caliber.artifact_count = load_count + date_count + variation_count + box_count
    
    # Get the global collection info
    collection_info = CollectionInfo.get_solo()
    
    context = {
        'calibers': calibers,
        'collection_name': collection_info.name,
        'collection_description': collection_info.description,
    }

    return render(request, 'collection/landing.html', context)


def dashboard(request, caliber_code):
    """Dashboard for a specific caliber with optimized statistics queries"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Default theme color if not specified
    if not caliber.theme_color:
        caliber.theme_color = "#3a7ca5"  # Default blue

    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Calculate statistics using optimized queries
    stats = {}
    
    # Single query for countries, manufacturers, headstamps, and headstamp images
    basic_counts = Country.objects.filter(caliber=caliber).aggregate(
        countries=Count('id'),
        manufacturers=Count('manufacturer', distinct=True),
        headstamps=Count('manufacturer__headstamps', distinct=True),
        headstamp_images=Count('manufacturer__headstamps__id', 
                              filter=~Q(manufacturer__headstamps__image='') & 
                                     ~Q(manufacturer__headstamps__image=None), 
                              distinct=True)
    )
    
    # Single query for load stats
    load_stats = Load.objects.filter(
        headstamp__manufacturer__country__caliber=caliber
    ).aggregate(
        count=Count('id'),
        image_count=Count('id', filter=~Q(image='') & ~Q(image=None))
    )
    
    # Single query for date stats
    date_stats = Date.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber
    ).aggregate(
        count=Count('id'),
        image_count=Count('id', filter=~Q(image='') & ~Q(image=None))
    )
    
    # Single query for all variation stats (both load and date variations)
    variation_stats = Variation.objects.filter(
        Q(load__headstamp__manufacturer__country__caliber=caliber) |
        Q(date__load__headstamp__manufacturer__country__caliber=caliber)
    ).aggregate(
        load_variations=Count('id', filter=Q(load__isnull=False)),
        load_var_images=Count('id', filter=Q(load__isnull=False) & 
                                            ~Q(image='') & ~Q(image=None)),
        date_variations=Count('id', filter=Q(date__isnull=False)),
        date_var_images=Count('id', filter=Q(date__isnull=False) & 
                                             ~Q(image='') & ~Q(image=None))
    )
    
    # Get ContentType objects for box queries
    from django.contrib.contenttypes.models import ContentType
    country_content_type = ContentType.objects.get_for_model(Country)
    manufacturer_content_type = ContentType.objects.get_for_model(Manufacturer)
    headstamp_content_type = ContentType.objects.get_for_model(Headstamp)
    load_content_type = ContentType.objects.get_for_model(Load)
    date_content_type = ContentType.objects.get_for_model(Date)
    variation_content_type = ContentType.objects.get_for_model(Variation)
    
    # Get IDs for box query (optimized with single queries)
    country_ids = list(Country.objects.filter(caliber=caliber).values_list('id', flat=True))
    manufacturer_ids = list(Manufacturer.objects.filter(country__caliber=caliber).values_list('id', flat=True))
    headstamp_ids = list(Headstamp.objects.filter(manufacturer__country__caliber=caliber).values_list('id', flat=True))
    load_ids = list(Load.objects.filter(headstamp__manufacturer__country__caliber=caliber).values_list('id', flat=True))
    date_ids = list(Date.objects.filter(load__headstamp__manufacturer__country__caliber=caliber).values_list('id', flat=True))
    
    # Get variation IDs (both types)
    load_var_ids = list(Variation.objects.filter(
        load__headstamp__manufacturer__country__caliber=caliber, 
        load__isnull=False
    ).values_list('id', flat=True))
    date_var_ids = list(Variation.objects.filter(
        date__load__headstamp__manufacturer__country__caliber=caliber, 
        date__isnull=False
    ).values_list('id', flat=True))
    
    # Single query for box stats
    box_stats = Box.objects.filter(
        Q(content_type=country_content_type, object_id__in=country_ids) |
        Q(content_type=manufacturer_content_type, object_id__in=manufacturer_ids) |
        Q(content_type=headstamp_content_type, object_id__in=headstamp_ids) |
        Q(content_type=load_content_type, object_id__in=load_ids) |
        Q(content_type=date_content_type, object_id__in=date_ids) |
        Q(content_type=variation_content_type, object_id__in=load_var_ids + date_var_ids)
    ).aggregate(
        count=Count('id'),
        image_count=Count('id', filter=~Q(image='') & ~Q(image=None))
    )
    
    # Assign all stats
    stats['countries'] = basic_counts['countries'] or 0
    stats['manufacturers'] = basic_counts['manufacturers'] or 0
    stats['headstamps'] = basic_counts['headstamps'] or 0
    stats['headstamp_images'] = basic_counts['headstamp_images'] or 0
    stats['loads'] = load_stats['count'] or 0
    stats['load_images'] = load_stats['image_count'] or 0
    stats['dates'] = date_stats['count'] or 0
    stats['date_images'] = date_stats['image_count'] or 0
    stats['load_variations'] = variation_stats['load_variations'] or 0
    stats['load_variation_images'] = variation_stats['load_var_images'] or 0
    stats['date_variations'] = variation_stats['date_variations'] or 0
    stats['date_variation_images'] = variation_stats['date_var_images'] or 0
    stats['boxes'] = box_stats['count'] or 0
    stats['box_images'] = box_stats['image_count'] or 0
    
    # Keep your existing recent activities functionality
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
    recent_boxes = Box.objects.filter(
        Q(content_type=country_content_type, object_id__in=country_ids) |
        Q(content_type=manufacturer_content_type, object_id__in=manufacturer_ids) |
        Q(content_type=headstamp_content_type, object_id__in=headstamp_ids) |
        Q(content_type=load_content_type, object_id__in=load_ids) |
        Q(content_type=date_content_type, object_id__in=date_ids) |
        Q(content_type=variation_content_type, object_id__in=load_var_ids + date_var_ids)
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

    # Get collection info for the header
    collection_info = CollectionInfo.get_solo()
    
    context = {
        # Add collection name for the header in ref_base.html
        'collection_name': collection_info.name,
        
        # Include collection description if you need it (optional)
        'collection_description': collection_info.description,
    }
    
    return render(request, 'collection/user_guide.html', context)

def support_view(request):
    """Support page view"""
    
    # Get collection info for the header
    collection_info = CollectionInfo.get_solo()
    
    context = {
        # Add collection name for the header in ref_base.html
        'collection_name': collection_info.name,
        
        # Include collection description if you need it (optional)
        'collection_description': collection_info.description,
    }
    
    return render(request, 'collection/support.html', context)


# class CollectionResourcesView(View):
#     """View for displaying reference materials and collector resources"""
    
#     def get(self, request):
#         # Get the global collection info
#         collection_info = CollectionInfo.get_solo()
        
#         # Get all calibers for the dropdown
#         calibers = Caliber.objects.all().order_by('order', 'name')
        
#         context = {
#             'collection_name': collection_info.name,
#             'calibers': calibers,
#             # Add any additional context needed for resource pages
#         }
        
#         return render(request, 'collection/resources.html', context)


@cache_control(max_age=3600)  # Cache for 1 hour
def serve_media_file(request, path):
    """View to serve media files directly from Django"""
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(open(file_path, 'rb'))
    
    raise Http404(f"Media file {path} not found")
