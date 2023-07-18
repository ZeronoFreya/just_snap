from . import n_panel

classes = (
    n_panel,    
)

def register():
    for cls in classes:
        try:
            cls.register()
        except Exception as e:
            print(e)

def unregister():
    for cls in classes:
        try:
            cls.unregister()
        except Exception as e:
            print(e)
