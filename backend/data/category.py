import json

# Load JSON file
with open('products.json', 'r') as file:
    data = json.load(file)

# Extract unique categories
categories = set()

for product in data.values():
    if "category" in product:
        categories.add(product["category"])

# Print categories
for category in categories:
    print(category)