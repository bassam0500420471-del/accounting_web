from products.models import Product


# زيادة المخزون
def increase_stock(product_id, qty):
    try:
        product = Product.objects.get(id=product_id)
        product.stock = (product.stock or 0) + qty
        product.save()
    except Product.DoesNotExist:
        pass


# إنقاص المخزون
def decrease_stock(product_id, qty):
    try:
        product = Product.objects.get(id=product_id)
        product.stock = (product.stock or 0) - qty
        product.save()
    except Product.DoesNotExist:
        pass


# إعادة المخزون عند تعديل أو حذف الفاتورة
def restore_stock_for_purchase(items):
    for item in items:
        decrease_stock(item.product_id, item.qty)


def restore_stock_for_sales(items):
    for item in items:
        increase_stock(item.product_id, item.qty)
