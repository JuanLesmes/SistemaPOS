class LoginViewController:
    def __init__(self, parent, main_controller, db):
        self.parent = parent
        self.main_controller = main_controller
        self.db = db
        from view.login_view import LoginView
        self.view = LoginView(self.parent, self)
        self.initialize()

    def initialize(self):
        pass

    def event_go_admin(self):
        self.main_controller.show_admin_view()

    def event_go_sales(self):
        self.main_controller.show_sales_view()

    def event_go_report(self):
        self.main_controller.show_sales_report_view()

    def event_verify_auditlog_password(self):
        self.main_controller.event_verify_auditlog_password()


