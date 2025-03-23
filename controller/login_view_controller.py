class LoginViewController:
    def __init__(self, parent, main_controller, db):
        self.parent = parent
        self.main_controller = main_controller
        self.db = db
        from view.login_view import StonksView
        self.view = StonksView(self.parent, self)
        self.initialize()

    def initialize(self):
        pass

    def event_go_admin(self):
        self.main_controller.show_admin_view()
