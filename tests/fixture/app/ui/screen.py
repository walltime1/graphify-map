from app.core.store import save


def show(items):
    return save(items, "out.json")
