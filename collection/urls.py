from django.urls import path
from . import views

urlpatterns = [
    # Landing page
    path('', views.landing, name='landing'),
    
    path('<str:caliber_code>/', views.dashboard, name='dashboard'),

    path('<str:caliber_code>/countries/', views.country_list, name='country_list'),
    path('<str:caliber_code>/countries/create/', views.country_create, name='country_create'),
    path('<str:caliber_code>/countries/<int:country_id>/', views.country_detail, name='country_detail'),
    path('<str:caliber_code>/countries/<int:country_id>/update/', views.country_update, name='country_update'),
    path('<str:caliber_code>/countries/<int:country_id>/delete/', views.country_delete, name='country_delete'),

    path('<str:caliber_code>/countries/<int:country_id>/manufacturers/create/', views.manufacturer_create, name='manufacturer_create'),
    path('<str:caliber_code>/manufacturers/<int:manufacturer_id>/', views.manufacturer_detail, name='manufacturer_detail'),
    path('<str:caliber_code>/manufacturers/<int:manufacturer_id>/edit/', views.manufacturer_update, name='manufacturer_update'),
    path('<str:caliber_code>/manufacturers/<int:manufacturer_id>/delete/', views.manufacturer_delete, name='manufacturer_delete'),
    path('<str:caliber_code>/manufacturers/<int:manufacturer_id>/move/', views.manufacturer_move, name='manufacturer_move'),
    path('<str:caliber_code>/headstamps/<int:headstamp_id>/', views.headstamp_detail, name='headstamp_detail'),
    path('<str:caliber_code>/headstamps/<int:headstamp_id>/edit/', views.headstamp_update, name='headstamp_update'),
    path('<str:caliber_code>/headstamps/<int:headstamp_id>/delete/', views.headstamp_delete, name='headstamp_delete'),
    path('<str:caliber_code>/manufacturers/<int:manufacturer_id>/headstamps/create/', views.headstamp_create, name='headstamp_create'),
    path('<str:caliber_code>/headstamps/<int:headstamp_id>/move/', views.headstamp_move, name='headstamp_move'),

    # New headstamp source management URLs
    path('<str:caliber_code>/headstamps/<int:headstamp_id>/add-source/', views.headstamp_add_source, name='headstamp_add_source'),
    path('<str:caliber_code>/headstamps/<int:headstamp_id>/remove-source/<int:source_id>/', views.headstamp_remove_source, name='headstamp_remove_source'),

    # Load URLs
    path('<str:caliber_code>/loads/<int:load_id>/', views.load_detail, name='load_detail'),
    path('<str:caliber_code>/headstamps/<int:headstamp_id>/loads/create/', views.load_create, name='load_create'),
    path('<str:caliber_code>/loads/<int:load_id>/update/', views.load_update, name='load_update'),
    path('<str:caliber_code>/loads/<int:load_id>/delete/', views.load_delete, name='load_delete'),
    path('<str:caliber_code>/loads/<int:load_id>/add-source/', views.load_add_source, name='load_add_source'),
    path('<str:caliber_code>/loads/<int:load_id>/remove-source/<int:source_id>/', views.load_remove_source, name='load_remove_source'),
    path('<str:caliber_code>/loads/<int:load_id>/move/', views.load_move, name='load_move'),

    # Date URLs
    path('<str:caliber_code>/dates/<int:date_id>/', views.date_detail, name='date_detail'),
    path('<str:caliber_code>/loads/<int:load_id>/add-date/', views.date_create, name='date_create'),
    path('<str:caliber_code>/dates/<int:date_id>/update/', views.date_update, name='date_update'),
    path('<str:caliber_code>/dates/<int:date_id>/delete/', views.date_delete, name='date_delete'),
    path('<str:caliber_code>/dates/<int:date_id>/add-source/', views.date_add_source, name='date_add_source'),
    path('<str:caliber_code>/dates/<int:date_id>/remove-source/<int:source_id>/', views.date_remove_source, name='date_remove_source'),

    # Variation URLs
    path('<str:caliber_code>/variations/<int:variation_id>/', views.variation_detail, name='variation_detail'),
    path('<str:caliber_code>/loads/<int:load_id>/add-variation/', views.variation_create_for_load, name='variation_create_for_load'),
    path('<str:caliber_code>/dates/<int:date_id>/add-variation/', views.variation_create_for_date, name='variation_create_for_date'),
    path('<str:caliber_code>/variations/<int:variation_id>/update/', views.variation_update, name='variation_update'),
    path('<str:caliber_code>/variations/<int:variation_id>/delete/', views.variation_delete, name='variation_delete'),
    path('<str:caliber_code>/variations/<int:variation_id>/add-source/', views.variation_add_source, name='variation_add_source'),
    path('<str:caliber_code>/variations/<int:variation_id>/remove-source/<int:source_id>/', views.variation_remove_source, name='variation_remove_source'),

    # Box URLs
    path('<str:caliber_code>/boxes/<int:box_id>/', views.box_detail, name='box_detail'),
    path('<str:caliber_code>/boxes/create/<str:model_name>/<int:object_id>/', views.box_create, name='box_create'),
    path('<str:caliber_code>/boxes/<int:box_id>/update/', views.box_update, name='box_update'),
    path('<str:caliber_code>/boxes/<int:box_id>/delete/', views.box_delete, name='box_delete'),
    path('<str:caliber_code>/boxes/<int:box_id>/sources/add/', views.box_add_source, name='box_add_source'),
    path('<str:caliber_code>/boxes/<int:box_id>/sources/<int:source_id>/remove/', views.box_remove_source, name='box_remove_source'),
    path('<str:caliber_code>/boxes/<int:box_id>/move/', views.box_move, name='box_move'),

    # Temporary URLs:
    path('<str:caliber_code>/headstamps/', views.country_list, name='headstamp_list'),
    path('<str:caliber_code>/loads/', views.country_list, name='load_list'),
    # path('<str:caliber_code>/loads/<int:pk>/', views.country_list, name='load_detail'),
    # path('<str:caliber_code>/headstamps/<int:pk>/', views.country_list, name='headstamp_detail'),
    path('<str:caliber_code>/boxes/', views.country_list, name='box_list'), 
    path('<str:caliber_code>/boxes/<int:pk>/', views.country_list, name='box_detail'),
    path('<str:caliber_code>/dates/<int:pk>/', views.country_list, name='date_detail'),
    path('<str:caliber_code>/variations/<int:pk>/', views.country_list, name='variation_detail'),
    
    # Search functionality
    path('<str:caliber_code>/search/', views.record_search, name='record_search'),
    path('<str:caliber_code>/headstamp-header-search/', views.headstamp_header_search, name='headstamp_header_search'),
    
    # Advanced search URLs for different entity types
    path('<str:caliber_code>/search/manufacturer/', views.manufacturer_search, name='manufacturer_search'),
    path('<str:caliber_code>/search/headstamp/', views.headstamp_search, name='headstamp_search'), 
    path('<str:caliber_code>/search/load/', views.load_search, name='load_search'),
    path('<str:caliber_code>/search/box/', views.box_search, name='box_search'),

    # Add new items (placeholders)
    path('<str:caliber_code>/add-artifact/', views.add_artifact, name='add_artifact'),
    path('<str:caliber_code>/import_records/', views.import_records, name='import_records'),
    path('<str:caliber_code>/download-results/', views.download_results, name='download_results'),
    path('<str:caliber_code>/import-images/', views.import_images, name='import_images'),
    
    # Support and docs
    # Without caliber (will use first active caliber)
    path('documentation/user-guide/', views.user_guide_view, name='user_guide'),
    path('documentation/support/', views.support_view, name='support'),

    # With caliber specified in URL
    path('<str:caliber_code>/documentation/user-guide/', views.user_guide_view, name='user_guide_with_caliber'),
    path('<str:caliber_code>/documentation/support/', views.support_view, name='support_with_caliber'),
]

