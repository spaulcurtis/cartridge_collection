from django.shortcuts import render
from ..models import CollectionInfo


def nine_mm_guide(request):

    # Get the global collection info
    collection_info = CollectionInfo.get_solo()
    
    context = {
    'collection_name': collection_info.name,
    }

    return render(request, 'collection/reference/9mm_para_guide.html', context)

def collection_highlights(request):

    # Get the global collection info
    collection_info = CollectionInfo.get_solo()
    
    context = {
    'collection_name': collection_info.name,
    }

    return render(request, 'collection/reference/collection_highlights.html', context)
