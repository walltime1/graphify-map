class Repo:
    def add(self, item):
        if item is None:
            return 0
        return self.count() + 1

    def count(self):
        return 0
