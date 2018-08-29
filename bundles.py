import bigcommerce
import time
import smtplib
import os
import boto3
import json
import requests
import logging

clientID = os.environ['clientID']
store_hash = os.environ['store_hash']
accessToken = os.environ['accessToken']

api = bigcommerce.api.BigcommerceApi(
client_id = clientID,
store_hash=store_hash,
access_token=accessToken)

onepage = 250 # 250 is the max items per page for bigcommerce

class NetworkError(RuntimeError):
    pass
 
def retryer(max_retries=5, timeout=10):
    def wraps(func):
        request_exceptions = (
            bigcommerce.exception.RateLimitingException,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError
        )

        def inner(*args, **kwargs):
            for i in range(max_retries):
                try:    
                    result = func(*args, **kwargs)
                except request_exceptions:
                    
                    print("retrying)")
                    time.sleep(timeout*i)
                    continue
                else:
                    return result
            else:
                raise NetworkError 
        return inner
    return wraps

def start():
    print("------ START ------")
    
def end():
    print("------ END ------")
    
@retryer(max_retries=5, timeout=10)
def reverbsync(idNo):
    customfields = api.ProductCustomFields.all(parentid=idNo)
    for i in customfields:
        
        try:
            if(i['name']) == 'reverb_sync':
                reverbsync = i
        except:
            print("reverbsync failed", i)
            logging.exception('')
    try:
        print(reverbsync)
    except:
        print('failed, trying update first')
        api.ProductCustomFields.create(parentid=idNo,name='reverb_sync',text='off')
        customfields = api.ProductCustomFields.all(parentid=idNo)
        for i in customfields:
            if(i['name']) == 'reverb_sync':
                reverbsync = i
        print('trying again')
        logging.exception('')
        try:
            print(reverbsync)
        except:
            print('failed again')
            logging.exception('')
    return reverbsync

@retryer(max_retries=5, timeout=10)
def getbody(event):
    body = json.loads(event['body'])
    return(body)
    
@retryer(max_retries=5, timeout=10)
def categories(categoryname):
    categories = api.Categories.all(limit=onepage)
    for each in categories:
        if each['name'] == categoryname:
            categorynumber = each['id']
    return(categorynumber)
    
@retryer(max_retries=5, timeout=10)
def getproduct(idNo):
    product = api.Products.get(idNo)
    return(product)

@retryer(max_retries=5, timeout=10)
def getcustomfields(parentid):
    customfields = api.ProductCustomFields.all(parentid=parentid)
    return(customfields)
    
@retryer(max_retries=5, timeout=10)
def updateproduct(idNo,availability,availability_description,inventory_tracking):
    product = api.Products.get(idNo).update(availability=availability, availability_description=availability_description,inventory_tracking=inventory_tracking)
    return(product)
    
@retryer(max_retries=5, timeout=10)
def updatecustomfields(parentid,id,name,text):
    customfields = api.ProductCustomFields.get(parentid=parentid,id=id).update(name=name,text=text)
    return(customfields)
    
@retryer(max_retries=5, timeout=10)
def updateinventory(idNo,inventory_level):
    inventoryupdate = api.Products.get(idNo).update(inventory_level=inventory_level)
    return(inventoryupdate)
    
@retryer(max_retries=5, timeout=10)
def getcategoryproducts(categoryname):
    products = api.Products.all(category=categories("Bundles"), limit = onepage)
    return(products)
    
def bundles(event, context):
    start()
    
    body = getbody(event)
    
    hookid = body['data']['inventory']['product_id']
    hookinv = body['data']['inventory']['value']
    apiscope = body['scope']
    
    changedproduct = getproduct(hookid)
    
    changedproductcategories = changedproduct['categories']
    changedproductname = changedproduct['name']
    changedproductidNo = changedproduct['id']
    changedproductsku = changedproduct['sku']
    changedproductupc = changedproduct['upc']
    changedproductprice = changedproduct['price']
    changedproductinventory_tracking = changedproduct['inventory_tracking']
    changedproductupc = changedproduct['upc']
    changedproductis_free_shipping = changedproduct['is_free_shipping']
    changedproductinv = changedproduct['inventory_level']
    
    reverbsyncdata = reverbsync(changedproductidNo)
    
    print(hookid, changedproductname, "inventory has been updated to", hookinv, "& is now", changedproductinv)
    
    # if categories("Ignore") in changedproductcategories:
    #     print("ignoring!")
    # if (changedproductinv == 0
    # and categories("Ignore") not in changedproductcategories):
    #     if categories("Discontinued") in changedproductcategories:
    #         print("discontinue this thing")
    #     if categories("Pre-order") in changedproductcategories:
    #         print("this thing is pre-order")
    #     if categories("Back-order") in changedproductcategories:
    #         print("This thing is backordered")
    #     else:
    #         print("Out Of Stock")
    # if (changedproductinv > 0
    # and categories("Ignore") not in changedproductcategories):
    #     print(changedproductname, "is in-stock")
        
        # if ('available' not in changedproduct['availability'] 
        # or "In stock, ships within 24 hours" not in changedproduct['availability_description']
        # or changedproductinventory_tracking != "simple"):
        #     availability='available'
        #     availability_description="In stock, ships within 24 hours"
        #     inventory_tracking = "simple"
        #     product = updateproduct(hookid,availability,availability_description,inventory_tracking)
        #     print("product now stocked")
        # else: 
        #     print("product already in stock")
        # if (reverbsyncdata['text'] != "force"):
        #     try:
        #         parentid = changedproductidNo
        #         id = reverbsyncdata['id']
        #         name='reverb_sync'
        #         text='force'
        #         customfields = updatecustomfields(parentid,id,name,text)
        #         print("reverb now synced")
        #     except:
        #         print("ERROR!!!! REVERB SYNC UPDATE FAILED!!!")
        #         logging.exception('')
        # else:
        #     print("reverb already synced")

    pagecounter = 1
    bundles = getcategoryproducts("Bundles")
    
    icounter = 0
    for each in bundles:
        idNo = each['id']
        
        customfields = getcustomfields(idNo)
        icounter += 1
        
        if idNo == hookid and apiscope == "store/product/inventory/order/updated":
            for i in customfields:
                if i['text'].isdigit():
                    
                    requiredforbundle = int(i['text'])
                    subproductID = i['name']
                    subproduct = getproduct(subproductID)
                    subinvupdateqty = subproduct['inventory_level'] + (requiredforbundle * hookinv)
                    print(subinvupdateqty, subproduct['name'], "update")
                    subinvupdate = updateinventory(subproductID,inventory_level)
                    print(subinvupdate)
        
        print(each['inventory_level'],"/", each['name'], "/", idNo)
        bundlelist = []
        
        for i in customfields:
            if i['text'].isdigit():
                
                requiredforbundle = int(i['text'])
                subproductID = i['name']
                subproduct = getproduct(subproductID)
                print(requiredforbundle, subproduct['name'], "per bundle")
                print(subproduct['inventory_level'], subproduct['name'], "in stock")
                bundleamount = int(subproduct['inventory_level'] / int(requiredforbundle))
                print(bundleamount, "bundles can be created with", subproduct['name'])
                bundlelist.append(bundleamount)
        bundlestockupdate = min(bundlelist)
        print(bundlestockupdate,"bundles can be created for", each['name'])
        if bundlestockupdate > 0:
            
            inventory_level=bundlestockupdate
            inventory_tracking="simple"
            availability='available'
            availability_description="In stock, ships within 24 hours"
            update = updateproduct(idNo,availability,availability_description,inventory_tracking)
            updatebundleinventory = updateinventory(idNo,inventory_level)
            print(inventory_level, idNo, each['name'], availability,availability_description)
            print(update)
            print(updatebundleinventory)
        else: 
            
            inventory_level = bundlestockupdate
            updatebundleinventory = updateinventory(idNo,inventory_level)
            print(updatebundleinventory)
        print(bundlestockupdate,"bundles have been created for", each['name'])
        print(icounter, "products inventoried")
    end()
    return {"statusCode": 200}
