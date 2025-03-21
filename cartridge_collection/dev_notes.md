# Building a new one from the ground up.

## To Do list

## Adding Caliber

#### Recommended Approach: Caliber as a Top-Level Model
I recommend the second approach for several reasons:

1. Simpler infrastructure: One database is easier to manage, back up, and deploy
2. Consistent schema: All calibers share the same database schema
3. Cross-caliber querying: You can easily query across calibers if needed
4. Authentication sharing: Users and permissions are naturally shared
5. Easier development: No need to juggle multiple database connections

#### Implementation Steps

1. Add the Caliber model at the top of your models.py file
2. Modify all models to include a ForeignKey to Caliber
3. Update unique constraints to include caliber (e.g., Country name is unique per caliber)
4. Add middleware to set the active caliber based on URL or user preference:

'''

    # collection/middleware.py
    class CaliberMiddleware:
        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            # Get caliber from URL if present (e.g., /9mm/countries/)
            path_parts = request.path.strip('/').split('/')
            if path_parts and Caliber.objects.filter(code=path_parts[0]).exists():
                request.active_caliber = path_parts[0]
            else:
                # Default to user preference or system default
                request.active_caliber = request.session.get('active_caliber', '9mm')
                
            return self.get_response(request)
'''
5. Update URLs to include caliber previxes

'''

    # urls.py
    urlpatterns = [
        path('admin/', admin.site.urls),
        path('<slug:caliber_code>/', include('collection.urls')),
        # Add a default redirect to preferred caliber
        path('', RedirectView.as_view(url='/9mm/')),
]

'''

6. Updat eviews to filter by the active caliber:

'''

    def country_list(request, caliber_code):
        caliber = get_object_or_404(Caliber, code=caliber_code)
        countries = Country.objects.filter(caliber=caliber)
        return render(request, 'collection/country_list.html', {
            'countries': countries,
            'caliber': caliber,
        })

'''

7. Add a caliber switcher in your main template

'''

    <div class="caliber-switcher">
        <label for="caliber-select">Collection:</label>
        <select id="caliber-select" onchange="location = this.value;">
            {% for cal in all_calibers %}
                <option value="/{{ cal.code }}/" {% if cal.code == active_caliber %}selected{% endif %}>
                    {{ cal.name }}
                </option>
            {% endfor %}
        </select>
    </div>

'''


