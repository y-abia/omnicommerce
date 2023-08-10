import frappe
from datetime import datetime
from frappe.utils.password import update_password
from mymb_ecommerce.controllers.solr_crud import add_document_to_solr
from bs4 import BeautifulSoup
from slugify import slugify
from datetime import datetime


config = Configurations()



@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_webiste_items(limit=None, time_laps=None, page=1,  filters=None, fetch_property=False, fetch_media=False , fetch_price=False):
    
    return {
        "data": 'Hello world',
        "count": 5
    }

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_items_in_solr(limit=None, page=None, time_laps=None, filters=None, fetch_property=False, fetch_media=False , fetch_price=False):
    items = get_webiste_items(limit=limit, page=page,time_laps=time_laps, filters=filters, fetch_property=fetch_property, fetch_media=fetch_media, fetch_price=fetch_price)

    success_items = []
    failure_items = []
    skipped_items = []

    for item in items["data"]:
        solr_document = transform_to_solr_document(item)

        # LOGIC TO CHANGE BELOW
        if solr_document is None or not item.get('properties') or not item.get('medias'):
            sku = item.get('carti', "No code available")
            skipped_items.append(sku)
            frappe.log_error(f"Warning: Skipped Item in solr  SKU: {sku} , D: {solr_document['id']}  to Solr", f"Skipped document with SKU: {sku} due to missing slug or prices or properties or medias. {solr_document}")
            continue

        result = add_document_to_solr(solr_document)
        if result['status'] == 'success':
            success_items.append(solr_document['sku'])
        else:
            failure_items.append(solr_document['sku'])
            frappe.log_error(title=f"Error: Import Item in solr SKU: {solr_document['sku']} ID: {solr_document['id']} ", message=f"Failed to add document with SKU: {solr_document['sku']} to Solr. Reason: {result['reason']}" )

    return {
        "data": {
            "success_items": success_items,
            "failure_items": failure_items,
            "skipped_items": skipped_items,
            "summary": {
                "success": len(success_items),
                "failure": len(failure_items),
                "skipped": len(skipped_items)
            }
        }
    }




def transform_to_solr_document(item):
    prices = item.get('prices', None)
    properties = item.get('properties', [])
    id =  item.get('oarti', None)
    sku = item.get('carti', None)
    
    properties_map = {property['property_id']: property['value'] for property in properties}
    name = properties_map.get('title_frontend', item.get('tarti', None))
    name = BeautifulSoup(name, 'html.parser').get_text() if name else None

    slug = "det/"+slugify(name + "-" + sku) if name and sku else None
    # If slug is None, return None to skip this item
    if slug is None or prices is None or id is None or sku is None:
        return None
    
    short_description = properties_map.get('short_description', item.get('tarti_swebx', None))
    short_description = BeautifulSoup(short_description, 'html.parser').get_text() if short_description else None
    description = properties_map.get('long_description', None)
    description = BeautifulSoup(description, 'html.parser').get_text() if description else None

    brand = properties_map.get('brand', None)
    images = [item['path'] + '/' + item['filename'] for item in item.get('medias', [])]

    

    net_price = prices.get('net_price', 0)
    net_price_with_vat = prices.get('net_price_with_vat', 0)
    gross_price = prices.get('gross_price', 0)
    gross_price_with_vat = prices.get('gross_price_with_vat', 0)
    availability = prices.get('availability', 0)
    is_promo = prices.get('is_promo', False)
    is_best_promo = prices.get('is_best_promo', False)
    promo_price = prices.get('promo_price', 0)
    promo_price_with_vat = prices.get('promo_price_with_vat', 0)

    discount_value = discount_percent = None
    if is_promo and gross_price_with_vat:
        discount_value = round(gross_price_with_vat - promo_price_with_vat,2)
        discount_percent= int((1 - promo_price_with_vat/gross_price_with_vat)*100) if gross_price_with_vat else None
        
    start_promo_date_str = prices.get('start_promo_date', None)
    end_promo_date_str = prices.get('end_promo_date', None)
    # Transform date strings to Solr date format if they are not None
    start_promo_date = datetime.strptime(start_promo_date_str, "%d/%m/%y").strftime("%Y-%m-%dT%H:%M:%SZ") if start_promo_date_str else None
    end_promo_date = datetime.strptime(end_promo_date_str, "%d/%m/%y").strftime("%Y-%m-%dT%H:%M:%SZ") if end_promo_date_str else None
    
    solr_document = {
        "id": id,
        "sku": sku,
        "availability": availability,
        "name": name,
        "name_nostem": name,
        "short_description": short_description,
        "short_description_nostem": short_description,
        "description": description,
        "description_nostem": description,
        "sku_father": item.get('sku_father', None),
        "num_images": len(images),
        "images": images,
        "id_brand": item.get('id_brand', []),
        "id_father": item.get('id_father', None),
        "keywords": item.get('keywords', None),
        "model": item.get('model', None),
        "model_nostem": item.get('model_nostem', None),
        "discount_value":discount_value,
        "discount_percent":discount_percent,
        "slug": slug,
        "synonymous": item.get('synonymous', None),
        "synonymous_nostem": item.get('synonymous_nostem', None),
        "gross_price": gross_price,
        "gross_price_with_vat": gross_price_with_vat,
        "net_price": net_price,
        "net_price_with_vat":net_price_with_vat ,
        "promo_code": prices.get('promo_code', None),
        "promo_price": promo_price,
        "promo_price_with_vat": promo_price_with_vat,
        "is_promo": is_promo,
        "is_best_promo": is_best_promo,
        "promo_title": prices.get('promo_title', None),
        "start_promo_date": start_promo_date,
        "end_promo_date": end_promo_date,
        "discount": prices.get('discount', [None]*6),
        "discount_extra": prices.get('discount_extra', [None]*3),
        "pricelist_type": prices.get('pricelist_type', None),
        "pricelist_code": prices.get('pricelist_code', None)
    }

    return solr_document
