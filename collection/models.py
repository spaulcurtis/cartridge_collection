from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError

# ===============================
# Extensible Lookup Table Models
# ===============================

class LoadType(models.Model):
    """Extensible lookup table for load types"""
    value = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_common = models.BooleanField(default=False)
    legacy_mappings = models.TextField(blank=True, help_text="Comma-separated list of legacy values that map to this")
    
    def __str__(self):
        return self.display_name
    
    class Meta:
        ordering = ['-is_common', 'display_name']

class BulletType(models.Model):
    """Extensible lookup table for bullet types"""
    value = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_common = models.BooleanField(default=False)
    legacy_mappings = models.TextField(blank=True, help_text="Comma-separated list of legacy values that map to this")
    
    def __str__(self):
        return self.display_name
    
    class Meta:
        ordering = ['-is_common', 'display_name']

class CaseType(models.Model):
    """Extensible lookup table for case types"""
    value = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_common = models.BooleanField(default=False)
    legacy_mappings = models.TextField(blank=True, help_text="Comma-separated list of legacy values that map to this")
    
    def __str__(self):
        return self.display_name
    
    class Meta:
        ordering = ['-is_common', 'display_name']

class PrimerType(models.Model):
    """Extensible lookup table for primer types"""
    value = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_common = models.BooleanField(default=False)
    legacy_mappings = models.TextField(blank=True, help_text="Comma-separated list of legacy values that map to this")
    
    def __str__(self):
        return self.display_name
    
    class Meta:
        ordering = ['-is_common', 'display_name']

class PAColor(models.Model):
    """Extensible lookup table for primer annulus colors"""
    value = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_common = models.BooleanField(default=False)
    legacy_mappings = models.TextField(blank=True, help_text="Comma-separated list of legacy values that map to this")
    
    def __str__(self):
        return self.display_name
    
    class Meta:
        ordering = ['-is_common', 'display_name']

# ===============================
# Fixed Choice Constants
# ===============================

CREDIBILITY_CHOICES = [
    (1, '1 - In Collection'),
    (2, '2 - Reliable Reference'),
    (3, '3 - Secondary Source'),
    (4, '4 - Questionable'),
    (5, '5 - Unverified'),
]

ARTIFACT_TYPE_CHOICES = [
    ('box', 'Box'),
    ('photo', 'Photograph'),
    ('drawing', 'Drawing'),
    ('label', 'Label'),
    ('document', 'Document'),
    ('other', 'Other'),
]

# ===============================
# Source Models
# ===============================

class Source(models.Model):
    """Information about sources of collection data"""
    name = models.CharField("Source Name", max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

# ===============================
# Base Model Classes
# ===============================

class BaseEntity(models.Model):
    """Base class for non-artifact entities (taxonomic/organizational)"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    note = models.TextField("Notes", blank=True, null=True)
    
    class Meta:
        abstract = True

class BaseCollectionItem(models.Model):
    """Abstract base class for physical artifacts in the collection"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(blank=True, null=True)
    cc = models.IntegerField("Credibility Code", choices=CREDIBILITY_CHOICES, default=1)
    col_date = models.DateField("Collection Date", blank=True, null=True)
    price = models.DecimalField("Price/Value", max_digits=10, decimal_places=2, blank=True, null=True)
    note = models.TextField("Notes", blank=True, null=True)
    image = models.ImageField(upload_to='artifacts/', blank=True, null=True)
    
    def image_count(self):
        """Return 1 if this item has an image, 0 otherwise"""
        return 1 if self.image else 0
    
    def total_image_count(self):
        """Base implementation for total image count"""
        return self.image_count()
        
    def box_count(self):
        """Count directly attached boxes"""
        content_type = ContentType.objects.get_for_model(self)
        return Box.objects.filter(content_type=content_type, object_id=self.pk).count()
    
    def total_box_count(self):
        """Base implementation for total box count"""
        return self.box_count()
    
    class Meta:
        abstract = True

# ===============================
# Main Collection Models
# ===============================

class Caliber(models.Model):
    """Top-level model representing a caliber collection"""
    code = models.CharField(max_length=20, unique=True)  # e.g., "9mm", "45acp"
    name = models.CharField(max_length=100)  # e.g., "9mm Parabellum", ".45 ACP"
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='calibers/', blank=True, null=True)
    theme_color = models.CharField(max_length=20, blank=True, null=True, help_text="Hex color code, e.g. #3a7ca5")
    order = models.PositiveIntegerField(default=0, help_text="Display order on landing page")
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['order', 'name']

class Country(BaseEntity):
    """Country model - represents countries of origin"""
    caliber = models.ForeignKey(Caliber, on_delete=models.CASCADE)
    name = models.CharField("Country Code/Name", max_length=100, unique=True)
    full_name = models.CharField("Full Country Name", max_length=255, blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    def total_box_count(self):
        """Count boxes under this country and all its children"""
        # Direct boxes
        content_type = ContentType.objects.get_for_model(self)
        count = Box.objects.filter(content_type=content_type, object_id=self.pk).count()
        
        # Add boxes from manufacturers
        for manuf in self.manufacturer_set.all():
            count += manuf.total_box_count()
            
        return count
    
    class Meta:
        verbose_name_plural = "Countries"
        ordering = ['name']

class Manufacturer(BaseEntity):
    """Manufacturer model - represents cartridge manufacturers"""
    code = models.CharField("Manufacturer Code", max_length=100)
    name = models.CharField("Manufacturer Name", max_length=255, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    
    def __str__(self):
        return f"{self.code}" if not self.name else f"{self.code} - {self.name}"
    
    def total_box_count(self):
        """Count boxes under this manufacturer and all its children"""
        # Direct boxes
        content_type = ContentType.objects.get_for_model(self)
        count = Box.objects.filter(content_type=content_type, object_id=self.pk).count()
        
        # Add boxes from headstamps
        for headstamp in self.headstamps.all():
            count += headstamp.total_box_count()
            
        return count
    
    class Meta:
        ordering = ['country__name', 'code']
        unique_together = [['code', 'country']]

class Headstamp(models.Model):
    """Headstamp model - not a physical artifact but needs images and credibility"""
    code = models.CharField("Headstamp Code", max_length=100)
    name = models.CharField("Headstamp Name", max_length=255, blank=True, null=True)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT, related_name='headstamps')
    primary_manufacturer = models.ForeignKey(
        Manufacturer, on_delete=models.PROTECT, 
        related_name='case_headstamps', 
        blank=True, null=True,
        help_text="Manufacturer who produced the case"
    )
    cc = models.IntegerField("Credibility Code", choices=CREDIBILITY_CHOICES, default=1)
    note = models.TextField("Notes", blank=True, null=True)
    image = models.ImageField(upload_to='headstamps/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.code}" if not self.name else f"{self.code} - {self.name}"
    
    def image_count(self):
        """Return 1 if this item has an image, 0 otherwise"""
        return 1 if self.image else 0
    
    def total_image_count(self):
        """Include images from this headstamp and all its descendants"""
        count = self.image_count()
        
        # Add images from loads
        for load in self.loads.all():
            count += load.total_image_count()
            
        return count
    
    def box_count(self):
        """Count directly attached boxes"""
        content_type = ContentType.objects.get_for_model(self)
        return Box.objects.filter(content_type=content_type, object_id=self.pk).count()
    
    def total_box_count(self):
        """Count boxes under this headstamp and all its children"""
        count = self.box_count()
        
        # Add boxes from loads
        for load in self.loads.all():
            count += load.total_box_count()
            
        return count
    
    def add_source(self, source, date=None, note=None):
        """Add a source to this headstamp"""
        return HeadstampSource.objects.create(
            headstamp=self,
            source=source,
            date_sourced=date,
            note=note
        )
    
    def get_sources(self):
        """Get all sources for this headstamp"""
        return Source.objects.filter(headstampsource__headstamp=self)
    
    class Meta:
        ordering = ['manufacturer__country__name', 'manufacturer__code', 'code']
        unique_together = [['code', 'manufacturer']]

class HeadstampSource(models.Model):
    """Link between headstamps and sources"""
    headstamp = models.ForeignKey(Headstamp, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    date_sourced = models.DateField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.headstamp} - {self.source}"
    
    class Meta:
        unique_together = [['headstamp', 'source']]

class Load(BaseCollectionItem):
    """Load model - represents cartridges in the collection"""
    cart_id = models.CharField("Cartridge ID", max_length=20, unique=True)
    load_type = models.ForeignKey(LoadType, on_delete=models.PROTECT, related_name='loads')
    bullet = models.ForeignKey(BulletType, on_delete=models.PROTECT, related_name='loads', blank=True, null=True)
    is_magnetic = models.BooleanField("Is Magnetic", default=False)
    case_type = models.ForeignKey(CaseType, on_delete=models.PROTECT, related_name='loads', blank=True, null=True)
    primer = models.ForeignKey(PrimerType, on_delete=models.PROTECT, related_name='loads', blank=True, null=True)
    pa_color = models.ForeignKey(PAColor, on_delete=models.PROTECT, related_name='loads', blank=True, null=True)
    headstamp = models.ForeignKey(Headstamp, on_delete=models.PROTECT, related_name='loads')
    
    def __str__(self):
        return f"{self.cart_id}" if not self.load_type else f"{self.cart_id} - {self.load_type}"
    
    def total_image_count(self):
        """Include images from this load and all its descendants"""
        count = super().total_image_count()
        
        # Add images from dates
        for date in self.dates.all():
            count += date.total_image_count()
            
        # Add images from load variations
        for variation in self.load_variations.all():
            count += variation.total_image_count()
            
        return count
    
    def total_box_count(self):
        """Count boxes under this load and all its children"""
        count = super().total_box_count()
        
        # Add boxes from dates
        for date in self.dates.all():
            count += date.total_box_count()
            
        # Add boxes from load variations
        for variation in self.load_variations.all():
            count += variation.total_box_count()
            
        return count
    
    def add_source(self, source, date=None, note=None):
        """Add a source to this load"""
        return LoadSource.objects.create(
            load=self,
            source=source,
            date_sourced=date,
            note=note
        )
    
    def get_sources(self):
        """Get all sources for this load"""
        return Source.objects.filter(loadsource__load=self)
    
    def save(self, *args, **kwargs):
        # Automatically generate cart_id if not provided
        if not self.cart_id and not self.pk:
            # Get the next available ID
            last_load = Load.objects.order_by('-pk').first()
            next_id = (last_load.pk + 1) if last_load else 1
            self.cart_id = f"L{next_id}"
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['headstamp__manufacturer__country__name', 'headstamp__code', 'cart_id']

class LoadSource(models.Model):
    """Link between loads and sources"""
    load = models.ForeignKey(Load, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    date_sourced = models.DateField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.load} - {self.source}"
    
    class Meta:
        unique_together = [['load', 'source']]

class Date(BaseCollectionItem):
    """Date model - represents date/lot instances of loads"""
    cart_id = models.CharField("Date/Lot ID", max_length=20, unique=True)
    year = models.CharField("Year", max_length=10, blank=True, null=True)
    lot_month = models.CharField("Lot/Month", max_length=50, blank=True, null=True)
    load = models.ForeignKey(Load, on_delete=models.PROTECT, related_name='dates')
    
    def __str__(self):
        year_lot = f"{self.year or ''} {self.lot_month or ''}".strip()
        return f"{self.cart_id}" if not year_lot else f"{self.cart_id} - {year_lot}"
    
    def total_image_count(self):
        """Include images from this date and all its descendants"""
        count = super().total_image_count()
        
        # Add images from date variations
        for variation in self.date_variations.all():
            count += variation.total_image_count()
            
        return count
    
    def total_box_count(self):
        """Count boxes under this date and all its children"""
        count = super().total_box_count()
        
        # Add boxes from date variations
        for variation in self.date_variations.all():
            count += variation.total_box_count()
            
        return count
    
    def add_source(self, source, date=None, note=None):
        """Add a source to this date"""
        return DateSource.objects.create(
            date=self,
            source=source,
            date_sourced=date,
            note=note
        )
    
    def get_sources(self):
        """Get all sources for this date"""
        return Source.objects.filter(datesource__date=self)
    
    def save(self, *args, **kwargs):
        # Automatically generate cart_id if not provided
        if not self.cart_id and not self.pk:
            # Get the next available ID
            last_date = Date.objects.order_by('-pk').first()
            next_id = (last_date.pk + 1) if last_date else 1
            self.cart_id = f"D{next_id}"
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['load__headstamp__manufacturer__country__name', 'load__cart_id', 'year', 'lot_month']

class DateSource(models.Model):
    """Link between dates and sources"""
    date = models.ForeignKey(Date, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    date_sourced = models.DateField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.date} - {self.source}"
    
    class Meta:
        unique_together = [['date', 'source']]

class Variation(BaseCollectionItem):
    """Variation model - represents variations of loads or dates"""
    cart_id = models.CharField("Variation ID", max_length=20, unique=True)
    load = models.ForeignKey(Load, on_delete=models.PROTECT, blank=True, null=True, related_name='load_variations')
    date = models.ForeignKey(Date, on_delete=models.PROTECT, blank=True, null=True, related_name='date_variations')
    
    def __str__(self):
        parent = self.load or self.date
        parent_type = "Load" if self.load else "Date"
        return f"{self.cart_id}" if not self.description else f"{self.cart_id} - {self.description}"
    
    def clean(self):
        """Ensure either load or date is set, but not both"""
        if (self.load and self.date) or (not self.load and not self.date):
            raise ValidationError("Variation must have either load or date set, but not both")
    
    def add_source(self, source, date=None, note=None):
        """Add a source to this variation"""
        return VariationSource.objects.create(
            variation=self,
            source=source,
            date_sourced=date,
            note=note
        )
    
    def get_sources(self):
        """Get all sources for this variation"""
        return Source.objects.filter(variationsource__variation=self)
    
    def save(self, *args, **kwargs):
        # Run validation
        self.clean()
        
        # Automatically generate cart_id if not provided
        if not self.cart_id and not self.pk:
            # Get the next available ID
            last_var = Variation.objects.order_by('-pk').first()
            next_id = (last_var.pk + 1) if last_var else 1
            self.cart_id = f"V{next_id}"
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['cart_id']

class VariationSource(models.Model):
    """Link between variations and sources"""
    variation = models.ForeignKey(Variation, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    date_sourced = models.DateField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.variation} - {self.source}"
    
    class Meta:
        unique_together = [['variation', 'source']]

class Box(BaseCollectionItem):
    """Box model - represents boxes and other container artifacts"""
    bid = models.CharField("Box ID", max_length=20, unique=True)
    location = models.CharField("Physical Location", max_length=255, blank=True, null=True)
    art_type = models.CharField("Artifact Type", max_length=50, choices=ARTIFACT_TYPE_CHOICES, default='box')
    art_type_other = models.CharField("Other Artifact Type", max_length=100, blank=True, null=True,
                                     help_text="Specify if 'Other' is selected")
    
    # Generic relation to parent item
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    parent = GenericForeignKey('content_type', 'object_id')
    
    def __str__(self):
        return f"{self.bid}" if not self.description else f"{self.bid} - {self.description}"
    
    def add_source(self, source, date=None, note=None):
        """Add a source to this box"""
        return BoxSource.objects.create(
            box=self,
            source=source,
            date_sourced=date,
            note=note
        )
    
    def get_sources(self):
        """Get all sources for this box"""
        return Source.objects.filter(boxsource__box=self)
    
    def save(self, *args, **kwargs):
        # Automatically generate bid if not provided
        if not self.bid and not self.pk:
            # Get the next available ID
            last_box = Box.objects.order_by('-pk').first()
            next_id = (last_box.pk + 1) if last_box else 1
            self.bid = f"B{next_id}"
        super().save(*args, **kwargs)
    
    def parent_caliber(self):
        """
        Determines which caliber this box belongs to by traversing the parent relationship.
        """
        from django.contrib.contenttypes.models import ContentType
        from .models import Country, Manufacturer, Headstamp, Load, Date, Variation, Caliber
        
        if not hasattr(self, 'content_type') or not hasattr(self, 'object_id'):
            return None
        
        parent_model = self.content_type.model_class()
        
        try:
            parent_obj = parent_model.objects.get(pk=self.object_id)
        except parent_model.DoesNotExist:
            return None
        
        # Find the caliber based on the parent object type
        if parent_model == Country:
            return parent_obj.caliber
        elif parent_model == Manufacturer:
            return parent_obj.country.caliber
        elif parent_model == Headstamp:
            return parent_obj.manufacturer.country.caliber
        elif parent_model == Load:
            return parent_obj.headstamp.manufacturer.country.caliber
        elif parent_model == Date:
            return parent_obj.load.headstamp.manufacturer.country.caliber
        elif parent_model == Variation:
            # Handle both types of variations
            if parent_obj.load:
                return parent_obj.load.headstamp.manufacturer.country.caliber
            elif parent_obj.date:
                return parent_obj.date.load.headstamp.manufacturer.country.caliber
        
        return None

    def get_parent_display(self):
        """
        Returns a display string for the parent object.
        """
        if not hasattr(self, 'content_type') or not hasattr(self, 'object_id'):
            return "Unknown"
        
        parent_model = self.content_type.model_class()
        
        try:
            parent_obj = parent_model.objects.get(pk=self.object_id)
            
            # First check for cart_id which is used by Load, Date, and Variation
            if hasattr(parent_obj, 'cart_id') and parent_obj.cart_id:
                return parent_obj.cart_id
            # Then name for Country, possibly Manufacturer 
            elif hasattr(parent_obj, 'name') and parent_obj.name:
                return parent_obj.name
            # Then code for Headstamp, Manufacturer
            elif hasattr(parent_obj, 'code') and parent_obj.code:
                return parent_obj.code
            else:
                return f"{parent_model.__name__} #{parent_obj.pk}"
        except parent_model.DoesNotExist:
            return "Not Found"
        
    class Meta:
        ordering = ['bid']

class BoxSource(models.Model):
    """Link between boxes and sources"""
    box = models.ForeignKey(Box, on_delete=models.CASCADE)
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    date_sourced = models.DateField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.box} - {self.source}"
    
    class Meta:
        unique_together = [['box', 'source']]