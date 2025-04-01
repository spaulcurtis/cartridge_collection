from django.contrib import admin
from django.utils.html import format_html
from .models import (
    # Collection Info
    CollectionInfo,
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

# Register CollectionInfo model
@admin.register(CollectionInfo)
class CollectionInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

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

@admin.register(HeadstampSource)
class HeadstampSourceAdmin(admin.ModelAdmin):
    list_display = ('headstamp', 'source', 'date_sourced', 'note')
    search_fields = ('headstamp', 'source', 'note')
    ordering = ('headstamp',)

@admin.register(LoadSource)
class LoadSourceAdmin(admin.ModelAdmin):
    list_display = ('load', 'source', 'date_sourced', 'note')
    search_fields = ('load', 'source', 'note')
    ordering = ('load',)

@admin.register(DateSource)
class DateSourceAdmin(admin.ModelAdmin):
    list_display = ('date', 'source', 'date_sourced', 'note')
    search_fields = ('date', 'source', 'note')
    ordering = ('date',)

@admin.register(VariationSource)
class VariationSourceAdmin(admin.ModelAdmin):
    list_display = ('variation', 'source', 'date_sourced', 'note')
    search_fields = ('variation', 'source', 'note')
    ordering = ('variation',)

@admin.register(BoxSource)
class BoxSourceAdmin(admin.ModelAdmin):
    list_display = ('box', 'source', 'date_sourced', 'note')
    search_fields = ('box', 'source', 'note')
    ordering = ('box',)

# Country admin
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('caliber', 'name', 'short_name','full_name', 'id')
    search_fields = ('name', 'short_name', 'full_name', 'note')
    list_filter = ('caliber',)
    ordering = ('caliber', 'name',)

# Manufacturer admin
@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('country__caliber', 'code', 'name', 'country', 'id')
    list_filter = ('country__caliber', 'country',)
    search_fields = ('code', 'name', 'note')
    ordering = ('country__caliber', 'country__name', 'code')

# Headstamp admin with image display
@admin.register(Headstamp)
class HeadstampAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'manufacturer', 'primary_manufacturer', 'id')
    list_filter = ('manufacturer__country__caliber', 'manufacturer__country', 'manufacturer')
    search_fields = ('code', 'name', 'note')
    ordering = ('manufacturer__country__caliber', 'code')
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
    list_display = ('cart_id', 'headstamp', 'load_type', 'bullet', 'case_type', 'id')
    list_filter = ('headstamp__manufacturer__country__caliber','headstamp__manufacturer__country', 'load_type')
    search_fields = ('cart_id', 'description', 'note', 'headstamp__code')
    ordering = ('headstamp__manufacturer__country__caliber', 'id',)
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
    list_display = ('cart_id', 'year', 'lot_month', 'load','id')
    list_filter = ('load__headstamp__manufacturer__country__caliber', 'load__headstamp__manufacturer__country')
    search_fields = ('cart_id', 'year', 'lot_month', 'description', 'note')
    ordering = ('load__headstamp__manufacturer__country__caliber', 'id')
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
    list_display = ('cart_id', 'load', 'date', 'description', 'id')
    list_filter = ('cc',)
    search_fields = ('cart_id', 'description', 'note')
    ordering = ('id',)
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