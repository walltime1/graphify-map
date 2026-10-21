from app.core.repo import Repo
from app.core.store import save


def show(items):
    return save(items, "out.json")


def add_one():
    return Repo().add(1)
