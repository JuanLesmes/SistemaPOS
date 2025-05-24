from view.auditlog_view import AuditLogView

class AuditLogViewController:
    def __init__(self, parent, main_controller, db):
        self.parent = parent
        self.main_controller = main_controller
        self.db = db
        self.view = AuditLogView(self.parent, self)
        self.view.pack(fill="both", expand=True)

    def event_load_logs(self, date_str):
        logs = self.db.get_logs_by_date(date_str)
        self.view.show_logs(logs)

    def event_back(self):
        self.main_controller.show_login_view()