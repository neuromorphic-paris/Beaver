class FrameworkAbstraction:
    def __init__(self, file = None):
        self.Name = ''
        self.Modules = []
        self.EventsTypes = []
        self.Files = {'Documentation':'        ~ Generated with Beaver ~'} # Abstracted Files, not actual ones
        
        self.HasChameleon = False
        self.HasTariser = False

        if not file is None:
            self._LoadFramework(file)

    def _LoadFramework(self, file):
        None
