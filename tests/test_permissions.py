from model import permissions
from model.user import ROLE_ADMIN, ROLE_CASHIER, ROLE_SUPERVISOR, ROLES, User


def make_user(role: str, active: bool = True) -> User:
    return User(id=1, username="u", full_name="Usuario", role=role, active=active)


def test_admin_has_everything_and_cashier_sells_and_manages_stock():
    assert permissions.permissions_of(make_user(ROLE_ADMIN)) == permissions.ALL_PERMISSIONS
    assert permissions.permissions_of(make_user(ROLE_CASHIER)) == {
        permissions.SELL,
        permissions.INVENTORY_VIEW,
        permissions.INVENTORY_EDIT,
    }
    assert not permissions.can(make_user(ROLE_CASHIER), permissions.REPORTS)


def test_supervisor_cannot_manage_users_or_audit():
    supervisor = make_user(ROLE_SUPERVISOR)
    assert permissions.can(supervisor, permissions.SELL)
    assert permissions.can(supervisor, permissions.INVENTORY_EDIT)
    assert permissions.can(supervisor, permissions.VOID_SALE)
    assert not permissions.can(supervisor, permissions.MANAGE_USERS)
    assert not permissions.can(supervisor, permissions.AUDIT)


def test_inactive_or_missing_user_has_no_permissions():
    assert permissions.permissions_of(make_user(ROLE_ADMIN, active=False)) == frozenset()
    assert permissions.permissions_of(None) == frozenset()


def test_every_role_has_a_matrix_and_a_label():
    for role in ROLES:
        assert role in permissions.ROLE_PERMISSIONS
    for permission in permissions.ALL_PERMISSIONS:
        assert permission in permissions.PERMISSION_LABELS
