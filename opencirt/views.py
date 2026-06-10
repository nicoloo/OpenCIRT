from sharpcirt import views as _views

for _name in dir(_views):
    if not _name.startswith('_'):
        globals()[_name] = getattr(_views, _name)
