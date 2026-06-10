from sharpcirt import admin as _admin

# Re-export admin module attrs for Django admin autodiscovery
for _name in dir(_admin):
    if not _name.startswith('_'):
        globals()[_name] = getattr(_admin, _name)
