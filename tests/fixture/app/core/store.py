def save(items, path):
    for item in items:
        if item is None:
            continue
        if path.endswith(".json") and item:
            print(item)
    return len(items)
