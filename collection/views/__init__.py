from .common_views import (
    landing, dashboard, add_artifact, import_images, support_view, user_guide_view, 
)

from .search_views import (
    record_search, headstamp_search, load_search, manufacturer_search, 
    headstamp_header_search, headstamp_search
)
from .country_views import (
    country_list, country_detail, country_create, country_delete, country_update
)

from .manufacturer_views import (
    manufacturer_detail, manufacturer_create, manufacturer_delete, 
    manufacturer_update, manufacturer_move
)

from .headstamp_views import (
    headstamp_detail, headstamp_create, headstamp_delete, headstamp_update, 
    headstamp_add_source, headstamp_remove_source, headstamp_move
)

from .load_views import (
    load_detail, load_create, load_delete, load_update, load_add_source, 
    load_remove_source, load_move
)

from .date_views import (
    date_detail, date_create, date_delete, date_update, date_add_source, date_remove_source
)

from .variation_views import (
    variation_detail, variation_create_for_load, variation_create_for_date, 
    variation_delete, variation_update, variation_add_source, variation_remove_source
)

from .box_views import (
    box_detail, box_create, box_delete, box_update, box_add_source, box_remove_source,
    box_move
)


from .import_views import (
    import_records, download_results
)