from database.database import get_order, get_refund, get_customer

print("ORDER:")
print(get_order("ORD001"))

print("\nREFUND:")
print(get_refund("ORD002"))

print("\nCUSTOMER:")
print(get_customer("C001"))