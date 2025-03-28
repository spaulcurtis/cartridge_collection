from django.urls import path
from . import views

urlpatterns = [
    # Landing page
    path('', views.landing, name='landing'),
    
    # Caliber-specific URLs
    path('<str:caliber_code>/', views.dashboard, name='dashboard'),
    path('<str:caliber_code>/countries/', views.country_list, name='country_list'),
    path('<str:caliber_code>/countries/<int:country_id>/', views.country_detail, name='country_detail'),

    # Temporary URLs:
    path('<str:caliber_code>/headstamps/', views.country_list, name='headstamp_list'),
    path('<str:caliber_code>/loads/', views.country_list, name='load_list'),
    path('<str:caliber_code>/loads/<int:pk>/', views.country_list, name='load_detail'),
    path('<str:caliber_code>/headstamps/<int:pk>/', views.country_list, name='headstamp_detail'),
    path('<str:caliber_code>/boxes/', views.country_list, name='box_list'), 
    path('<str:caliber_code>/boxes/<int:pk>/', views.country_list, name='box_detail'),
    path('<str:caliber_code>/dates/<int:pk>/', views.country_list, name='date_detail'),
    path('<str:caliber_code>/variations/<int:pk>/', views.country_list, name='variation_detail'),
    
    # Search functionality (placeholders)
    path('<str:caliber_code>/search/', views.record_search, name='record_search'),
    path('<str:caliber_code>/headstamp-search/', views.headstamp_search, name='headstamp_search'),
    path('<str:caliber_code>/advanced-search/', views.advanced_search, name='advanced_search'),
    
    # Add new items (placeholders)
    path('<str:caliber_code>/add-artifact/', views.add_artifact, name='add_artifact'),
    path('<str:caliber_code>/import_records/', views.import_records, name='import_records'),
    path('<str:caliber_code>/download-results/', views.download_results, name='download_results'),
    path('<str:caliber_code>/import-images/', views.import_images, name='import_images'),
    
    # Support and docs
    path('documentation/', views.documentation, name='documentation'),
    path('support/', views.support, name='support'),
]
