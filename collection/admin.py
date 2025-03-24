from django.contrib import admin
from django.utils.html import format_html
from .models import (
    # Lookup tables
    LoadType, BulletType, CaseType, PrimerType, PAColor,
    # Entity models
    Caliber, Source, Country, Manufacturer, Headstamp,
    # Collection items
    Load, Date, Variation, Box,
    # Source relationships
    HeadstampSource, LoadSource, DateSource, VariationSource, BoxSource
)

# Register lookup tables with basic admin interfaces
class LookupAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'value', 'is_common', 'id')
    list_filter = ('is_common',)
    search_fields = ('display_name', 'value', 'legacy_mappings')
    ordering = ('-is_common', 'display_name')
    list_editable = ('is_common',)

admin.site.register(LoadType, LookupAdmin)
admin.site.register(BulletType, LookupAdmin)
admin.site.register(CaseType, LookupAdmin)
admin.site.register(PrimerType, LookupAdmin)
admin.site.register(PAColor, LookupAdmin)

# Register Caliber model
@admin.register(Caliber)
class CaliberAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'id')
    list_filter = ('is_active',)
    search_fields = ('code', 'name', 'description')
    ordering = ('code',)
    list_editable = ('is_active',)

# Register Source model
@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'id')
    search_fields = ('name', 'description')
    ordering = ('name',)

# Country admin
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('caliber', 'name', 'full_name', 'id')
    search_fields = ('name', 'full_name', 'note')
    list_filter = ('caliber',)
    ordering = ('name',)

# Manufacturer admin
@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'country', 'id')
    list_filter = ('country',)
    search_fields = ('code', 'name', 'note')
    ordering = ('country__name', 'code')

# Headstamp admin with image display
@admin.register(Headstamp)
class HeadstampAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'manufacturer', 'primary_manufacturer', 'cc', 'image_tag', 'id')
    list_filter = ('manufacturer__country', 'cc', 'manufacturer')
    search_fields = ('code', 'name', 'note')
    ordering = ('manufacturer__country__name', 'manufacturer__code', 'code')
    readonly_fields = ('image_preview',)
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="auto" />', obj.image.url)
        return ""
    image_tag.short_description = 'Image'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" height="auto" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Image Preview'

# HeadstampSource inline for Headstamp admin
class HeadstampSourceInline(admin.TabularInline):
    model = HeadstampSource
    extra = 1

# Load admin with image display
@admin.register(Load)
class LoadAdmin(admin.ModelAdmin):
    list_display = ('cart_id', 'headstamp', 'load_type', 'bullet', 'case_type', 'is_magnetic', 'image_tag', 'id')
    list_filter = ('headstamp__manufacturer__country', 'load_type', 'case_type', 'is_magnetic', 'cc')
    search_fields = ('cart_id', 'description', 'note', 'headstamp__code')
    ordering = ('cart_id',)
    readonly_fields = ('image_preview',)
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="auto" />', obj.image.url)
        return ""
    image_tag.short_description = 'Image'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" height="auto" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Image Preview'

# LoadSource inline for Load admin
class LoadSourceInline(admin.TabularInline):
    model = LoadSource
    extra = 1

# Date admin with image display
@admin.register(Date)
class DateAdmin(admin.ModelAdmin):
    list_display = ('cart_id', 'year', 'lot_month', 'load', 'cc', 'image_tag', 'id')
    list_filter = ('load__headstamp__manufacturer__country', 'cc', 'year')
    search_fields = ('cart_id', 'year', 'lot_month', 'description', 'note')
    ordering = ('cart_id',)
    readonly_fields = ('image_preview',)
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="auto" />', obj.image.url)
        return ""
    image_tag.short_description = 'Image'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" height="auto" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Image Preview'

# DateSource inline for Date admin
class DateSourceInline(admin.TabularInline):
    model = DateSource
    extra = 1

# Variation admin with image display
@admin.register(Variation)
class VariationAdmin(admin.ModelAdmin):
    list_display = ('cart_id', 'load', 'date', 'description', 'cc', 'image_tag', 'id')
    list_filter = ('cc',)
    search_fields = ('cart_id', 'description', 'note')
    ordering = ('cart_id',)
    readonly_fields = ('image_preview',)
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="auto" />', obj.image.url)
        return ""
    image_tag.short_description = 'Image'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" height="auto" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Image Preview'

# VariationSource inline for Variation admin
class VariationSourceInline(admin.TabularInline):
    model = VariationSource
    extra = 1

# Box admin with image display
@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ('bid', 'description', 'art_type', 'content_type', 'object_id', 'cc', 'image_tag', 'id')
    list_filter = ('art_type', 'cc', 'content_type')
    search_fields = ('bid', 'description', 'location', 'note')
    ordering = ('bid',)
    readonly_fields = ('image_preview',)
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="auto" />', obj.image.url)
        return ""
    image_tag.short_description = 'Image'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" height="auto" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Image Preview'

# BoxSource inline for Box admin
class BoxSourceInline(admin.TabularInline):
    model = BoxSource
    extra = 1

# Add source inlines to the respective admin classes
HeadstampAdmin.inlines = [HeadstampSourceInline]
LoadAdmin.inlines = [LoadSourceInline]
DateAdmin.inlines = [DateSourceInline]
VariationAdmin.inlines = [VariationSourceInline]
BoxAdmin.inlines = [BoxSourceInline]