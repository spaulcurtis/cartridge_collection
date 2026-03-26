"""
Tool definitions and implementations for the Collection Assistant.
These functions query the Django database and return results that include
URLs for linking directly to detail pages.
"""

from django.urls import reverse
from collection.models import (
    Caliber, Country, Manufacturer, Headstamp, Load, Date, Variation, Box,
)


# --- Tool definitions for the Claude API ---
# These describe the tools to Claude so it knows when and how to call them.

TOOL_DEFINITIONS = [
    {
        "name": "search_headstamps",
        "description": (
            "Search for headstamps by text. Matches against headstamp code and name. "
            "Returns matching headstamps with their manufacturer, country, load count, "
            "and a link to the detail page. Use this when the user asks about a specific "
            "headstamp marking, wants to find headstamps, or asks what headstamps exist "
            "for a manufacturer or country. If there are many results, also returns a "
            "link to the full search results page."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "caliber_code": {
                    "type": "string",
                    "description": "The caliber code, e.g. '9mm' or '765'. If unknown, use '9mm'.",
                },
                "search_text": {
                    "type": "string",
                    "description": "Text to search for in headstamp codes and names.",
                },
                "country": {
                    "type": "string",
                    "description": "Optional: filter by country name (partial match).",
                },
                "manufacturer": {
                    "type": "string",
                    "description": "Optional: filter by manufacturer code (partial match).",
                },
            },
            "required": ["caliber_code", "search_text"],
        },
    },
    {
        "name": "get_record_details",
        "description": (
            "Get full details of a specific record by its Cart ID (e.g., L123, D45, V12, B7) "
            "or by its type and database ID. Returns all fields for the record, its position "
            "in the hierarchy, and a link to its detail page. Use this when the user asks "
            "about a specific item, references a Cart ID, or wants details about a particular "
            "load, date, variation, box, or headstamp."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "caliber_code": {
                    "type": "string",
                    "description": "The caliber code, e.g. '9mm' or '765'. If unknown, use '9mm'.",
                },
                "cart_id": {
                    "type": "string",
                    "description": (
                        "The Cart ID to look up. Loads start with L (e.g., L123), "
                        "Dates with D, Variations with V, Boxes with B. "
                        "For headstamps, use the headstamp code directly."
                    ),
                },
                "record_type": {
                    "type": "string",
                    "enum": ["load", "date", "variation", "box", "headstamp"],
                    "description": (
                        "The type of record. Usually inferred from the Cart ID prefix: "
                        "L=load, D=date, V=variation, B=box. Use 'headstamp' when "
                        "looking up a headstamp by its code."
                    ),
                },
            },
            "required": ["caliber_code", "cart_id"],
        },
    },
    {
        "name": "search_loads",
        "description": (
            "Search for loads (cartridges) by various criteria. Returns matching loads "
            "with key properties and links to detail pages. Use this when the user asks "
            "about cartridges with specific characteristics like case type, bullet type, "
            "country of origin, or manufacturer. Also useful for questions like 'what "
            "steel case loads do I have' or 'show me magnetic rounds from Finland'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "caliber_code": {
                    "type": "string",
                    "description": "The caliber code, e.g. '9mm' or '765'. If unknown, use '9mm'.",
                },
                "country": {
                    "type": "string",
                    "description": "Optional: filter by country name (partial match).",
                },
                "manufacturer": {
                    "type": "string",
                    "description": "Optional: filter by manufacturer code or name (partial match).",
                },
                "headstamp": {
                    "type": "string",
                    "description": "Optional: filter by headstamp code (partial match).",
                },
                "load_type": {
                    "type": "string",
                    "description": "Optional: filter by load type (e.g., 'Ball', 'Tracer', 'Blank').",
                },
                "bullet_type": {
                    "type": "string",
                    "description": "Optional: filter by bullet type (e.g., 'FMJ', 'JHP').",
                },
                "case_type": {
                    "type": "string",
                    "description": "Optional: filter by case type (e.g., 'Brass', 'Steel', 'Aluminum').",
                },
                "is_magnetic": {
                    "type": "boolean",
                    "description": "Optional: filter by magnetic property (true/false).",
                },
                "description": {
                    "type": "string",
                    "description": "Optional: search in load description text (partial match).",
                },
            },
            "required": ["caliber_code"],
        },
    },
    {
        "name": "browse_children",
        "description": (
            "Browse the collection hierarchy. Lists children of a given level with links. "
            "Use this when the user asks 'what countries are in the collection', 'what "
            "manufacturers are in Germany', 'what headstamps does DAG have', or 'what "
            "loads are under this headstamp'. Specify the parent level and optionally a "
            "parent name/code to filter."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "caliber_code": {
                    "type": "string",
                    "description": "The caliber code, e.g. '9mm' or '765'. If unknown, use '9mm'.",
                },
                "child_type": {
                    "type": "string",
                    "enum": ["country", "manufacturer", "headstamp", "load"],
                    "description": (
                        "The type of children to list. 'country' lists all countries, "
                        "'manufacturer' lists manufacturers (optionally within a country), "
                        "'headstamp' lists headstamps (optionally for a manufacturer), "
                        "'load' lists loads (optionally for a headstamp)."
                    ),
                },
                "parent_name": {
                    "type": "string",
                    "description": (
                        "Optional: the parent to filter by. For manufacturers, this is a "
                        "country name. For headstamps, this is a manufacturer code. For "
                        "loads, this is a headstamp code. Partial match is used."
                    ),
                },
            },
            "required": ["caliber_code", "child_type"],
        },
    },
]


# --- Tool implementations ---

MAX_RESULTS = 15  # Max individual results to return before suggesting search page


def execute_tool(tool_name, tool_input):
    """Dispatch a tool call to the appropriate function."""
    if tool_name == "search_headstamps":
        return search_headstamps(**tool_input)
    elif tool_name == "get_record_details":
        return get_record_details(**tool_input)
    elif tool_name == "search_loads":
        return search_loads(**tool_input)
    elif tool_name == "browse_children":
        return browse_children(**tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def search_headstamps(caliber_code, search_text, country=None, manufacturer=None):
    """Search headstamps by text, optionally filtered by country or manufacturer."""
    try:
        caliber = Caliber.objects.get(code__iexact=caliber_code)
    except Caliber.DoesNotExist:
        return {"error": f"Caliber '{caliber_code}' not found."}

    from django.db.models import Q, Count

    qs = Headstamp.objects.filter(
        manufacturer__country__caliber=caliber,
    ).select_related(
        'manufacturer', 'manufacturer__country'
    ).annotate(
        load_count=Count('loads', distinct=True)
    )

    # Text search on code and name
    qs = qs.filter(
        Q(code__icontains=search_text) | Q(name__icontains=search_text)
    )

    # Optional filters
    if country:
        qs = qs.filter(
            Q(manufacturer__country__name__icontains=country) |
            Q(manufacturer__country__full_name__icontains=country)
        )
    if manufacturer:
        qs = qs.filter(
            Q(manufacturer__code__icontains=manufacturer) |
            Q(manufacturer__name__icontains=manufacturer)
        )

    total_count = qs.count()
    results = []

    for hs in qs[:MAX_RESULTS]:
        url = reverse('headstamp_detail', args=[caliber_code, hs.id])
        results.append({
            "code": hs.code,
            "name": hs.name or "",
            "manufacturer": hs.manufacturer.code,
            "manufacturer_name": hs.manufacturer.name or "",
            "country": hs.manufacturer.country.name,
            "load_count": hs.load_count,
            "has_image": bool(hs.image),
            "url": url,
        })

    response = {
        "total_matches": total_count,
        "results": results,
    }

    # If too many results, include a link to the search page
    if total_count > MAX_RESULTS:
        search_url = reverse('headstamp_search', args=[caliber_code])
        params = [f"code={search_text}", "code_match_type=contains"]
        if country:
            params.append(f"country_id={_find_country_id(caliber, country)}")
        response["search_page_url"] = f"{search_url}?{'&'.join(params)}"
        response["note"] = (
            f"Showing first {MAX_RESULTS} of {total_count} results. "
            f"Use the search page link for the full list."
        )

    return response


def get_record_details(caliber_code, cart_id, record_type=None):
    """Get full details of a record by Cart ID or headstamp code."""
    try:
        caliber = Caliber.objects.get(code__iexact=caliber_code)
    except Caliber.DoesNotExist:
        return {"error": f"Caliber '{caliber_code}' not found."}

    # Infer record type from Cart ID prefix if not specified
    if not record_type:
        prefix = cart_id[0].upper() if cart_id else ""
        type_map = {"L": "load", "D": "date", "V": "variation", "B": "box"}
        record_type = type_map.get(prefix, "headstamp")

    try:
        if record_type == "load":
            return _get_load_details(caliber, caliber_code, cart_id)
        elif record_type == "date":
            return _get_date_details(caliber, caliber_code, cart_id)
        elif record_type == "variation":
            return _get_variation_details(caliber, caliber_code, cart_id)
        elif record_type == "box":
            return _get_box_details(caliber, caliber_code, cart_id)
        elif record_type == "headstamp":
            return _get_headstamp_details(caliber, caliber_code, cart_id)
        else:
            return {"error": f"Unknown record type: {record_type}"}
    except Exception as e:
        return {"error": f"Record not found: {str(e)}"}


def _get_load_details(caliber, caliber_code, cart_id):
    load = Load.objects.select_related(
        'headstamp', 'headstamp__manufacturer', 'headstamp__manufacturer__country',
        'load_type', 'bullet', 'case_type', 'primer', 'pa_color',
    ).get(
        cart_id__iexact=cart_id,
        headstamp__manufacturer__country__caliber=caliber,
    )
    url = reverse('load_detail', args=[caliber_code, load.id])
    return {
        "type": "load",
        "cart_id": load.cart_id,
        "url": url,
        "headstamp": load.headstamp.code,
        "manufacturer": load.headstamp.manufacturer.code,
        "country": load.headstamp.manufacturer.country.name,
        "load_type": str(load.load_type) if load.load_type else "",
        "bullet_type": str(load.bullet) if load.bullet else "",
        "case_type": str(load.case_type) if load.case_type else "",
        "primer": str(load.primer) if load.primer else "",
        "pa_color": str(load.pa_color) if load.pa_color else "",
        "is_magnetic": load.is_magnetic,
        "credibility": load.cc,
        "description": load.description or "",
        "acquisition_note": load.acquisition_note or "",
        "price": str(load.price) if load.price else "",
        "notes": load.note or "",
        "has_image": bool(load.image),
        "date_count": load.dates.count(),
        "variation_count": load.load_variations.count(),
    }


def _get_date_details(caliber, caliber_code, cart_id):
    date = Date.objects.select_related(
        'load', 'load__headstamp', 'load__headstamp__manufacturer',
        'load__headstamp__manufacturer__country',
    ).get(
        cart_id__iexact=cart_id,
        load__headstamp__manufacturer__country__caliber=caliber,
    )
    url = reverse('date_detail', args=[caliber_code, date.id])
    return {
        "type": "date",
        "cart_id": date.cart_id,
        "url": url,
        "year": date.year or "",
        "lot_month": date.lot_month or "",
        "load_cart_id": date.load.cart_id,
        "headstamp": date.load.headstamp.code,
        "manufacturer": date.load.headstamp.manufacturer.code,
        "country": date.load.headstamp.manufacturer.country.name,
        "credibility": date.cc,
        "description": date.description or "",
        "notes": date.note or "",
        "has_image": bool(date.image),
        "variation_count": date.date_variations.count(),
    }


def _get_variation_details(caliber, caliber_code, cart_id):
    # Try load variation first, then date variation
    try:
        var = Variation.objects.select_related(
            'load', 'load__headstamp', 'load__headstamp__manufacturer',
            'load__headstamp__manufacturer__country',
            'date', 'date__load', 'date__load__headstamp',
            'date__load__headstamp__manufacturer',
            'date__load__headstamp__manufacturer__country',
        ).get(
            cart_id__iexact=cart_id,
        )
    except Variation.DoesNotExist:
        return {"error": f"Variation '{cart_id}' not found."}

    # Verify caliber
    if var.load:
        var_caliber = var.load.headstamp.manufacturer.country.caliber
    elif var.date:
        var_caliber = var.date.load.headstamp.manufacturer.country.caliber
    else:
        return {"error": f"Variation '{cart_id}' has no parent."}

    if var_caliber != caliber:
        return {"error": f"Variation '{cart_id}' not found in {caliber_code}."}

    url = reverse('variation_detail', args=[caliber_code, var.id])
    result = {
        "type": "variation",
        "cart_id": var.cart_id,
        "url": url,
        "credibility": var.cc,
        "description": var.description or "",
        "notes": var.note or "",
        "has_image": bool(var.image),
    }

    if var.load:
        result["parent_type"] = "load"
        result["parent_cart_id"] = var.load.cart_id
        result["headstamp"] = var.load.headstamp.code
        result["manufacturer"] = var.load.headstamp.manufacturer.code
        result["country"] = var.load.headstamp.manufacturer.country.name
    elif var.date:
        result["parent_type"] = "date"
        result["parent_cart_id"] = var.date.cart_id
        result["load_cart_id"] = var.date.load.cart_id
        result["headstamp"] = var.date.load.headstamp.code
        result["manufacturer"] = var.date.load.headstamp.manufacturer.code
        result["country"] = var.date.load.headstamp.manufacturer.country.name

    return result


def _get_box_details(caliber, caliber_code, cart_id):
    try:
        box = Box.objects.select_related('content_type').get(bid__iexact=cart_id)
    except Box.DoesNotExist:
        return {"error": f"Box '{cart_id}' not found."}

    url = reverse('box_detail', args=[caliber_code, box.id])
    return {
        "type": "box",
        "box_id": box.bid,
        "url": url,
        "description": box.description or "",
        "art_type": box.art_type or "",
        "location": box.location or "",
        "credibility": box.cc,
        "notes": box.note or "",
        "has_image": bool(box.image),
        "parent_type": box.content_type.model if box.content_type else "",
        "parent": str(box.parent) if box.parent else "",
    }


def _get_headstamp_details(caliber, caliber_code, code):
    from django.db.models import Count

    hs = Headstamp.objects.select_related(
        'manufacturer', 'manufacturer__country', 'primary_manufacturer',
    ).annotate(
        load_count=Count('loads', distinct=True),
    ).get(
        code__iexact=code,
        manufacturer__country__caliber=caliber,
    )

    url = reverse('headstamp_detail', args=[caliber_code, hs.id])
    result = {
        "type": "headstamp",
        "code": hs.code,
        "name": hs.name or "",
        "url": url,
        "manufacturer": hs.manufacturer.code,
        "manufacturer_name": hs.manufacturer.name or "",
        "country": hs.manufacturer.country.name,
        "credibility": hs.cc,
        "notes": hs.note or "",
        "has_image": bool(hs.image),
        "load_count": hs.load_count,
    }
    if hs.primary_manufacturer:
        result["case_manufacturer"] = hs.primary_manufacturer.code
        result["case_manufacturer_name"] = hs.primary_manufacturer.name or ""

    return result


def search_loads(caliber_code, country=None, manufacturer=None, headstamp=None,
                 load_type=None, bullet_type=None, case_type=None,
                 is_magnetic=None, description=None):
    """Search loads by various criteria."""
    try:
        caliber = Caliber.objects.get(code__iexact=caliber_code)
    except Caliber.DoesNotExist:
        return {"error": f"Caliber '{caliber_code}' not found."}

    from django.db.models import Q

    qs = Load.objects.filter(
        headstamp__manufacturer__country__caliber=caliber,
    ).select_related(
        'headstamp', 'headstamp__manufacturer', 'headstamp__manufacturer__country',
        'load_type', 'bullet', 'case_type', 'primer', 'pa_color',
    )

    if country:
        qs = qs.filter(
            Q(headstamp__manufacturer__country__name__icontains=country) |
            Q(headstamp__manufacturer__country__full_name__icontains=country)
        )
    if manufacturer:
        qs = qs.filter(
            Q(headstamp__manufacturer__code__icontains=manufacturer) |
            Q(headstamp__manufacturer__name__icontains=manufacturer)
        )
    if headstamp:
        qs = qs.filter(headstamp__code__icontains=headstamp)
    if load_type:
        qs = qs.filter(
            Q(load_type__display_name__icontains=load_type) |
            Q(load_type__value__icontains=load_type)
        )
    if bullet_type:
        qs = qs.filter(
            Q(bullet__display_name__icontains=bullet_type) |
            Q(bullet__value__icontains=bullet_type)
        )
    if case_type:
        qs = qs.filter(
            Q(case_type__display_name__icontains=case_type) |
            Q(case_type__value__icontains=case_type)
        )
    if is_magnetic is not None:
        qs = qs.filter(is_magnetic=is_magnetic)
    if description:
        qs = qs.filter(
            Q(description__icontains=description) |
            Q(note__icontains=description)
        )

    total_count = qs.count()
    results = []

    for load in qs[:MAX_RESULTS]:
        url = reverse('load_detail', args=[caliber_code, load.id])
        results.append({
            "cart_id": load.cart_id,
            "url": url,
            "headstamp": load.headstamp.code,
            "manufacturer": load.headstamp.manufacturer.code,
            "country": load.headstamp.manufacturer.country.name,
            "load_type": str(load.load_type) if load.load_type else "",
            "bullet_type": str(load.bullet) if load.bullet else "",
            "case_type": str(load.case_type) if load.case_type else "",
            "is_magnetic": load.is_magnetic,
            "description": load.description or "",
            "has_image": bool(load.image),
        })

    response = {
        "total_matches": total_count,
        "results": results,
    }

    if total_count > MAX_RESULTS:
        search_url = reverse('load_search', args=[caliber_code])
        params = []
        if country:
            cid = _find_country_id(caliber, country)
            if cid:
                params.append(f"country_id={cid}")
        if manufacturer:
            mid = _find_manufacturer_id(caliber, manufacturer)
            if mid:
                params.append(f"manufacturer_id={mid}")
        if case_type:
            params.append(f"case_type_id=_text:{case_type}")
        if description:
            params.append(f"description={description}&description_match_type=contains")
        if is_magnetic is not None:
            params.append(f"is_magnetic={'true' if is_magnetic else 'false'}")
        query_string = f"?{'&'.join(params)}" if params else ""
        response["search_page_url"] = f"{search_url}{query_string}"
        response["note"] = (
            f"Showing first {MAX_RESULTS} of {total_count} results. "
            f"Use the search page link for the full list."
        )

    return response


def browse_children(caliber_code, child_type, parent_name=None):
    """List children at a given level in the hierarchy."""
    try:
        caliber = Caliber.objects.get(code__iexact=caliber_code)
    except Caliber.DoesNotExist:
        return {"error": f"Caliber '{caliber_code}' not found."}

    from django.db.models import Count, Q

    if child_type == "country":
        qs = Country.objects.filter(caliber=caliber).annotate(
            manufacturer_count=Count('manufacturer', distinct=True),
        ).order_by('name')

        results = []
        for c in qs[:MAX_RESULTS]:
            url = reverse('country_detail', args=[caliber_code, c.id])
            results.append({
                "name": c.name,
                "full_name": c.full_name or "",
                "manufacturer_count": c.manufacturer_count,
                "url": url,
            })

        return {
            "total_matches": qs.count(),
            "child_type": "country",
            "results": results,
        }

    elif child_type == "manufacturer":
        qs = Manufacturer.objects.filter(
            country__caliber=caliber,
        ).select_related('country').annotate(
            headstamp_count=Count('headstamps', distinct=True),
        ).order_by('code')

        if parent_name:
            qs = qs.filter(
                Q(country__name__icontains=parent_name) |
                Q(country__full_name__icontains=parent_name)
            )

        total_count = qs.count()
        results = []
        for m in qs[:MAX_RESULTS]:
            url = reverse('manufacturer_detail', args=[caliber_code, m.id])
            results.append({
                "code": m.code,
                "name": m.name or "",
                "country": m.country.name,
                "headstamp_count": m.headstamp_count,
                "url": url,
            })

        response = {
            "total_matches": total_count,
            "child_type": "manufacturer",
            "results": results,
        }
        if parent_name:
            response["filtered_by"] = parent_name
        if total_count > MAX_RESULTS:
            response["note"] = f"Showing first {MAX_RESULTS} of {total_count} results."
        return response

    elif child_type == "headstamp":
        qs = Headstamp.objects.filter(
            manufacturer__country__caliber=caliber,
        ).select_related(
            'manufacturer', 'manufacturer__country'
        ).annotate(
            load_count=Count('loads', distinct=True),
        ).order_by('code')

        if parent_name:
            qs = qs.filter(
                Q(manufacturer__code__icontains=parent_name) |
                Q(manufacturer__name__icontains=parent_name)
            )

        total_count = qs.count()
        results = []
        for hs in qs[:MAX_RESULTS]:
            url = reverse('headstamp_detail', args=[caliber_code, hs.id])
            results.append({
                "code": hs.code,
                "name": hs.name or "",
                "manufacturer": hs.manufacturer.code,
                "country": hs.manufacturer.country.name,
                "load_count": hs.load_count,
                "url": url,
            })

        response = {
            "total_matches": total_count,
            "child_type": "headstamp",
            "results": results,
        }
        if parent_name:
            response["filtered_by"] = parent_name
        if total_count > MAX_RESULTS:
            response["note"] = f"Showing first {MAX_RESULTS} of {total_count} results."
        return response

    elif child_type == "load":
        qs = Load.objects.filter(
            headstamp__manufacturer__country__caliber=caliber,
        ).select_related(
            'headstamp', 'headstamp__manufacturer',
            'load_type', 'bullet', 'case_type',
        ).order_by('cart_id')

        if parent_name:
            qs = qs.filter(headstamp__code__icontains=parent_name)

        total_count = qs.count()
        results = []
        for load in qs[:MAX_RESULTS]:
            url = reverse('load_detail', args=[caliber_code, load.id])
            results.append({
                "cart_id": load.cart_id,
                "headstamp": load.headstamp.code,
                "load_type": str(load.load_type) if load.load_type else "",
                "bullet_type": str(load.bullet) if load.bullet else "",
                "case_type": str(load.case_type) if load.case_type else "",
                "description": load.description or "",
                "url": url,
            })

        response = {
            "total_matches": total_count,
            "child_type": "load",
            "results": results,
        }
        if parent_name:
            response["filtered_by"] = parent_name
        if total_count > MAX_RESULTS:
            response["note"] = f"Showing first {MAX_RESULTS} of {total_count} results."
        return response

    else:
        return {"error": f"Unknown child type: {child_type}"}


# --- Helpers ---

def _find_country_id(caliber, name):
    """Find a country ID by partial name match. Returns ID or empty string."""
    from django.db.models import Q
    c = Country.objects.filter(
        caliber=caliber,
    ).filter(
        Q(name__icontains=name) | Q(full_name__icontains=name)
    ).first()
    return str(c.id) if c else ""


def _find_manufacturer_id(caliber, name):
    """Find a manufacturer ID by partial code/name match. Returns ID or empty string."""
    from django.db.models import Q
    m = Manufacturer.objects.filter(
        country__caliber=caliber,
    ).filter(
        Q(code__icontains=name) | Q(name__icontains=name)
    ).first()
    return str(m.id) if m else ""
