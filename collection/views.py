from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib import messages
from .models import Caliber

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
    
    context = {
        'calibers': calibers,
    }
    return render(request, 'collection/landing.html', context)

def dashboard(request, caliber_code):
    """Dashboard for a specific caliber"""
    # Get the current caliber
    caliber = get_object_or_404(Caliber, code=caliber_code)
    
    # Default theme color if not specified
    if not caliber.theme_color:
        caliber.theme_color = "#3a7ca5"  # Default blue

    # Get all calibers for the dropdown
    all_calibers = Caliber.objects.all().order_by('order', 'name')
    
    # Dummy statistics
    stats = {
        'countries': 48,
        'manufacturers': 237,
        'headstamps': 562,
        'headstamp_images': 286,
        'loads': 1243,
        'load_images': 452,
        'dates': 892,
        'date_images': 241,
        'load_variations': 346,
        'load_variation_images': 102,
        'date_variations': 201,
        'date_variation_images': 58,
        'boxes': 258,
        'box_images': 153,
    }
    
    # Empty recent items
    recent_headstamps = []
    recent_loads = []
    recent_boxes = []
    
    context = {
        'caliber': caliber,
        'all_calibers': all_calibers,
        'stats': stats,
        'recent_headstamps': recent_headstamps,
        'recent_loads': recent_loads,
        'recent_boxes': recent_boxes,
    }
    return render(request, 'collection/dashboard.html', context)

# Placeholder views for URLs used in the dashboard
def country_list(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'title': 'Countries',
        'message': 'This page is under construction'
    })

def record_search(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    messages.info(request, "Search functionality is not yet implemented")
    return redirect('dashboard', caliber_code=caliber.code)

def headstamp_search(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    messages.info(request, "Search functionality is not yet implemented")
    return redirect('dashboard', caliber_code=caliber.code)

def advanced_search(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'title': 'Advanced Search',
        'message': 'This page is under construction'
    })

def add_load(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'title': 'Add Load',
        'message': 'This page is under construction'
    })

def add_box(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'title': 'Add Box',
        'message': 'This page is under construction'
    })

def upload_images(request, caliber_code):
    caliber = get_object_or_404(Caliber, code=caliber_code)
    return render(request, 'collection/placeholder.html', {
        'caliber': caliber,
        'title': 'Upload Images',
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
