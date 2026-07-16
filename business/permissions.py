from django.db.models import Q
from django.http import Http404
from guardian.shortcuts import assign_perm, get_objects_for_user
from rest_framework import exceptions
from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User
from business.models import (
    BRANCH_SCOPED_MODELS,
    BUSINESS_SCOPED_MODELS,
    CRUD_ACTIONS,
    ROLES,
    Address,
    Branch,
    Business,
    Employee,
    EmployeeInvitation,
    biz_perm,
)

# Roles that should see business/branch-wide reports & dashboard stats.
# Plain employees (role_name == ROLES.EMPLOYEE, or no Employee record at
# all) only see data scoped to themselves — see `has_full_report_access`.
FULL_REPORT_ACCESS_ROLES = {
    ROLES.OWNER.value,
    ROLES.BUSINESS_ADMIN.value,
    ROLES.BRANCH_MANAGER.value,
}


def resolve_employee(user, business):
    """Return the caller's ``Employee`` record for this business, or None."""
    if not business or not user or not getattr(user, "is_authenticated", False):
        return None
    return (
        Employee.objects.filter(user=user, business=business)
        .select_related("role")
        .first()
    )


def has_full_report_access(user, business, employee=None):
    """True if ``user`` should see business/branch-wide reports & dashboard
    stats rather than being scoped to just their own orders/transactions.

    Owners, business admins, and branch managers get the full view. Plain
    employees (role_name == "employee") — and anyone with no Employee
    record at all — only see their own data.

    Note: this is intentionally *not* the same check as the
    ``can_view_*_branch`` guardian permissions used elsewhere, since plain
    employees are also granted those (to view/act on branch inventory,
    orders, etc. day to day) — reports/stats need a stricter, role-based
    gate instead of reusing that permission.
    """
    if business and getattr(business, "owner_id", None) == getattr(user, "id", None):
        return True
    if employee is None:
        employee = resolve_employee(user, business)
    return bool(
        employee
        and employee.role_id
        and employee.role.role_name in FULL_REPORT_ACCESS_ROLES
    )


class BusinessModelObjectPermission(BasePermission):

    def to_generic_action(self, action):
        if action == "list":
            return "view"
        if action == "create":
            return "add"
        if action == "update":
            return "change"
        if action == "destroy":
            return "delete"
        return "change"

    def has_permission(self, request, view):
        return has_business_permission(
            request, view.queryset.model, request.query_params.get("business_id")
        )

    def has_object_permission(self, request, view, obj):
        # DRF passes the object as the third positional argument; the previous
        # signature was missing it which raised TypeError on every detail call.
        return has_business_object_permission(
            request,
            view.queryset.model,
            request.query_params.get("business_id"),
            self.to_generic_action(view.action),
        )


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsEmployee(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.employees.filter(user=request.user).exists()


class IsOwnerOrEmployee(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            obj.owner == request.user
            or obj.employees.filter(user=request.user).exists()
        )


def has_business_permission(request, model, business: Business):
    # Assumes that user is authenticated

    user: User = request.user
    employee = Employee.objects.filter(user=user, business=business).first()

    if not employee:
        return False

    return employee.role.permissions.filter(
        content_type__model=model._meta.model_name
    ).exists()


def has_business_object_permission(request, model, business, generic_action="change"):

    user: User = request.user

    employee = Employee.objects.filter(user=user, business=business).first()

    if not employee:
        return False

    if request.method in SAFE_METHODS:
        return employee.role.permissions.filter(
            content_type__model=model._meta.model_name
        ).exists()

    return employee.role.permissions.filter(
        Q(codename=f"{generic_action}_" + model._meta.model_name)
        # | Q(codename="view_" + model._meta.model_name)
        # | Q(codename="delete_" + model._meta.model_name)
        # | Q(codename="change_" + model._meta.model_name)
    ).exists()


def make_business_permission(model_cls, *, get_business=None):
    """
    Factory that returns a DRF permission class scoped to *model_cls*.

    ``get_business(obj)`` is an optional callable that extracts the Business
    from a view object.  When omitted the default tries ``obj.business`` and
    then ``obj`` itself (for cases where the view object *is* the business).
    """

    def _default_get_business(obj):
        return getattr(obj, "business", obj)

    resolve_business = get_business or _default_get_business

    class _BusinessPermission(BasePermission):
        def has_permission(self, request, view):
            return bool(request.user and request.user.is_authenticated)

        def has_object_permission(self, request, view, obj):
            return has_business_object_permission(
                request, model_cls, resolve_business(obj)
            )

    _BusinessPermission.__name__ = f"{model_cls.__name__}Permission"
    _BusinessPermission.__qualname__ = f"{model_cls.__name__}Permission"
    return _BusinessPermission


# Concrete permission classes produced by the factory.
hasBusinessPermission = make_business_permission(Business)
hasBranchPermission = make_business_permission(Branch)
hasBusinessAddressPermission = make_business_permission(Address)
EmployeeInvitationPermission = make_business_permission(EmployeeInvitation)


class hasUserPermission(BasePermission):
    def has_permission(self, request, view):
        if view.action == "list" and request.user.is_superuser:
            return True
        elif view.action == "create":
            return True
        if view.action in ["retrieve", "partial_update", "update", "destroy"]:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if view.action in ["partial_update", "update", "destroy", "retrieve"]:
            return obj == request.user or request.user.is_superuser


class BusinessAddressPermission(BasePermission):
    """
    Address objects can be linked to a business directly (obj.business) or
    indirectly through a branch (obj.branches.first().business).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "business") and obj.business:
            business = obj.business
        elif obj.branches.exists():
            business = obj.branches.first().business
        else:
            return False
        return has_business_object_permission(request, Address, business)


# ---------------------------------------------------------------------------
# Role → model → allowed actions mapping.
# Each key is a model name (matching PERMISSIONED_MODELS), each value is a
# list of CRUD actions that role is permitted to perform at branch scope.
# Business-wide roles (owner / admin) receive all permissions on the business
# object itself, derived from PERMISSIONED_MODELS + CRUD_ACTIONS.
# ---------------------------------------------------------------------------

_BRANCH_MANAGER_PERMS: dict[str, list[str]] = {
    "group": ["view", "add", "change"],
    "customer": ["view", "add", "change"],
    "item": ["view", "add", "change"],
    "itemvariant": ["view", "add", "change"],
    "supplier": ["view", "add", "change"],
    "inventory": ["view", "add"],
    "inventorymovement": ["view", "add"],
    "order": ["view", "add", "change"],
    "transaction": ["view", "add"],
    "businesspaymentmethod": ["view", "change"],
    "property": ["view", "add", "change"],
    "supply": ["view", "add", "change"],
    "employee": ["view"],
    "employeeinvitation": ["view", "add"],
}

_EMPLOYEE_PERMS: dict[str, list[str]] = {
    "group": ["view"],
    "customer": ["view", "add"],
    "item": ["view", "add", "change"],
    "itemvariant": ["view", "add", "change"],
    "supplier": ["view"],
    "inventory": ["view"],
    "inventorymovement": ["view", "add"],
    "order": ["view", "add", "change"],
    "transaction": ["view", "add"],
    "businesspaymentmethod": ["view"],
    "property": ["view"],
    "supply": ["view", "add", "change"],
}

_BUSINESS_ADMIN_PERMS: dict[str, list[str]] = {
    # business-scoped — full CRUD on staff/org models; view-only on branch itself
    "branch": ["view", "add", "change"],
    "employee": ["view", "add", "change", "delete"],
    "address": ["view", "add", "change", "delete"],
    "employeeinvitation": ["view", "add", "change", "delete"],
    "group": ["view", "add", "change", "delete"],
    "customer": ["view", "add", "change", "delete"],
    # branch-scoped — full CRUD on core inventory/sales; limited on financial/read-only
    "order": ["view", "add", "change", "delete"],
    "item": ["view", "add", "change", "delete"],
    "itemvariant": ["view", "add", "change", "delete"],
    "inventorymovement": ["view", "add", "change"],
    "inventory": ["view", "add"],
    "property": ["view", "add", "change", "delete"],
    "supplier": ["view", "add", "change", "delete"],
    "businesspaymentmethod": ["view", "change"],
    "transaction": ["view", "add"],
    "giftcard": ["view"],
    "supply": ["view", "add", "change"],
}

# Owner receives full CRUD on every permissioned model.
_OWNER_PERMS: dict[str, list[str]] = {
    model: list(CRUD_ACTIONS) for model in BUSINESS_SCOPED_MODELS + BRANCH_SCOPED_MODELS
}

# Permissions on the business object — only for truly business-wide models.
_BUSINESS_OBJECT_PERMS: list[str] = [
    biz_perm(model, action, "business")
    for model in BUSINESS_SCOPED_MODELS
    for action in CRUD_ACTIONS
]

# Permissions granted on every branch for branch-scoped models.
_BRANCH_OBJECT_PERMS: list[str] = [
    biz_perm(model, action, "branch")
    for model in BRANCH_SCOPED_MODELS
    for action in CRUD_ACTIONS
]


def _split_perms_by_scope(
    model_actions: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """Return ``(branch_perms, business_perms)`` from a model→actions mapping.

    The scope is decided per-model: any model in ``BRANCH_SCOPED_MODELS`` gets
    branch-scoped permission codenames; anything else falls back to the
    business scope. This avoids generating perms such as ``can_view_group_branch``
    that are never declared on the ``Branch`` model.
    """
    branch_perms: list[str] = []
    business_perms: list[str] = []
    for model, actions in model_actions.items():
        scope = "branch" if model in BRANCH_SCOPED_MODELS else "business"
        bucket = branch_perms if scope == "branch" else business_perms
        for action in actions:
            bucket.append(biz_perm(model, action, scope))
    return branch_perms, business_perms


def _filter_was_requested(request) -> bool:
    """True when the caller passed a business/branch identifier in the
    query string or in a request header, even if it resolved to nothing.

    Used to distinguish "the caller asked about a specific business that does
    not exist (return empty)" from "the caller didn't filter at all (use
    everything the user can reach)".
    """
    query_keys = ("business", "business_id", "branch", "branch_id")
    if any(request.GET.get(key) for key in query_keys):
        return True
    header_keys = ("X-Business-Id", "X-Branch-Id")
    return any(request.headers.get(key) for key in header_keys)


def accessible_branches(request, model_name: str, action: str = "view"):
    """Return the queryset of branches where ``request.user`` holds a
    branch-scoped permission for ``model_name``.

    Resolution order:
      * ``request.branch`` is set → narrow to just that branch (subject to perm).
      * ``request.business`` is set → look across that business's branches.
      * Neither is set and the caller didn't request a specific business/branch
        → consider every branch the user can reach. This makes detail
        endpoints usable for owners/managers who hit a URL without filters.
      * Caller asked for a specific (but unresolved) business/branch → empty.
    """
    perm = biz_perm(model_name, action, "branch")
    user = request.user
    branch = getattr(request, "branch", None)
    business = getattr(request, "business", None)

    if branch:
        base = Branch.objects.filter(pk=branch.pk)
    elif business:
        base = business.branches.all()
    elif _filter_was_requested(request):
        # User explicitly asked for a business/branch that doesn't resolve.
        return Branch.objects.none()
    else:
        base = Branch.objects.all()

    return get_objects_for_user(user, perm, base, accept_global_perms=False)


def filter_queryset_by_branch(
    queryset,
    request,
    model_name: str,
    branch_field: str = "branch",
    action: str = "view",
):
    """Filter ``queryset`` to objects living in branches the user can ``action``.

    ``branch_field`` is the lookup path from the model to a ``Branch`` (e.g.
    ``"branch"``, ``"item__branch"``). Returns an empty queryset when no branch
    context is available or the user has no relevant perms.
    """
    branches = accessible_branches(request, model_name, action)
    if not branches.exists():
        return queryset.none()
    return queryset.filter(
        Q(**{f"{branch_field}__in": branches}) | Q(**{f"{branch_field}__isnull": True})
    )


class PermissionManager:
    """
    Translates Role.permissions (Django Permission M2M) into guardian
    object-level permission grants on the business / branch objects.

    Role.permissions is the single source of truth — this manager only
    reads from it and applies the appropriate guardian grants.  No
    hardcoded role-name logic lives here, so custom roles work for free.
    """

    def assign_branch_scoped_perms_for_branch(self, user, branch):
        """Grant every branch-scoped permission the user's role declares
        on a specific branch.  Called when a new branch is created so that
        existing owners / admins get access automatically.

        Falls back to the full _BRANCH_OBJECT_PERMS list when no employee
        record exists yet (e.g. during business creation before the owner
        employee row has been saved).
        """
        employee = (
            Employee.objects.filter(user=user, business=branch.business)
            .select_related("role")
            .first()
        )

        if employee and employee.role:
            codenames = list(
                employee.role.permissions.select_related("content_type")
                .filter(
                    Q(codename__endswith="_branch") | Q(content_type__model="branch")
                )
                .values_list("codename", flat=True)
            )
        else:
            codenames = _BRANCH_OBJECT_PERMS

        for codename in codenames:
            assign_perm(codename, user, branch)

    def assign_permissions_for_employee(self, employee):
        """Assign guardian object-level permissions to a user from their
        role's permissions.

        Split rules:
        - codename ends with ``_business`` **or** content_type is ``business``
          → granted on the business object.
        - codename ends with ``_branch`` **or** content_type is ``branch``
          → granted on the employee's branch (skipped when branch is None).
        - anything else (standard model perms like ``view_employee``) is only
          kept on Role.permissions for direct role-perm checks; no guardian
          object grant is needed.

        Call this whenever an employee is created or their role/branch changes.
        """
        if not employee.user or not employee.role:
            return

        user = employee.user
        business = employee.business
        branch = employee.branch

        business_codenames = []
        branch_codenames = []

        for perm in employee.role.permissions.select_related("content_type").all():
            codename = perm.codename
            model = perm.content_type.model

            if codename.endswith("_business") or model == "business":
                business_codenames.append(codename)
            elif codename.endswith("_branch") or model == "branch":
                branch_codenames.append(codename)

        for codename in business_codenames:
            assign_perm(codename, user, business)

        if branch:
            # Branch-specific employee or manager — grant perms on their branch only.
            for codename in branch_codenames:
                assign_perm(codename, user, branch)
        elif branch_codenames:
            # Business-wide role (owner, admin) with no assigned branch — grant
            # branch perms on every branch so they can access all of them.
            for b in business.branches.all():
                for codename in branch_codenames:
                    assign_perm(codename, user, b)


class BusinessLevelPermission(BasePermission):
    """
    The request is authenticated using Django's object-level permissions.
    It requires an object-permissions-enabled backend, such as Django Guardian.

    It ensures that the user is authenticated, and has the appropriate
    `add`/`change`/`delete` permissions on the object using .has_perms.

    This permission can only be applied against view classes that
    provide a `.queryset` attribute.
    """

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.can_add_%(model_name)s_business"],
        "PUT": ["%(app_label)s.can_change_%(model_name)s_business"],
        "PATCH": ["%(app_label)s.can_change_%(model_name)s_business"],
        "DELETE": ["%(app_label)s.can_delete_%(model_name)s_business"],
    }

    def get_required_object_permissions(self, method, model_cls):
        kwargs = {
            "app_label": "business",
            "model_name": model_cls._meta.model_name,
        }

        if method not in self.perms_map:
            raise exceptions.MethodNotAllowed(method)

        return [perm % kwargs for perm in self.perms_map[method]]

    def get_binding_object(self, request):
        """
        This method is used to get the binding object for the permission check.
        It can be overridden in subclasses to provide custom logic.
        """
        if request.method != "GET":
            if request.business:
                return request.business

            business = request.data.get("business")
            if not business:
                business = request.data.get("business_id")
            if business:
                request.business = Business.objects.filter(id=business).first()
                return request.business

        return request.business if hasattr(request, "business") else None

    def has_permission(self, request, view):
        user = request.user
        model_cls = view.queryset.model
        if request.method == "POST":
            business = request.data.get("business")
            if not business:
                business = request.data.get("business_id")
            if business:
                request.business = Business.objects.filter(id=business).first()
                perms = self.get_required_object_permissions(request.method, model_cls)
                return user.has_perms(perms, request.business)

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        # authentication checks have already executed via has_permission
        queryset = self._queryset(view)
        model_cls = queryset.model
        user = request.user
        business = self.get_binding_object(request)

        perms = self.get_required_object_permissions(request.method, model_cls)

        if not user.has_perms(perms, business):
            # If the user does not have permissions we need to determine if
            # they have read permissions to see 403, or not, and simply see
            # a 404 response.

            if request.method in SAFE_METHODS:
                # Read permissions already checked and failed, no need
                # to make another lookup.
                raise Http404

            read_perms = self.get_required_object_permissions("GET", model_cls)
            if not user.has_perms(read_perms, obj):
                raise Http404

            # Has read permissions.
            return False

        return True

    def _queryset(self, view):
        assert (
            hasattr(view, "get_queryset") or getattr(view, "queryset", None) is not None
        ), (
            "Cannot apply {} on a view that does not set "
            "`.queryset` or have a `.get_queryset()` method."
        ).format(
            self.__class__.__name__
        )

        if hasattr(view, "get_queryset"):
            queryset = view.get_queryset()
            assert queryset is not None, "{}.get_queryset() returned None".format(
                view.__class__.__name__
            )
            return queryset
        return view.queryset


class BranchLevelPermission(BusinessLevelPermission):
    """
    Permission class for branch-level permissions.
    It extends BusinessLevelPermission to ensure that the user has
    the appropriate permissions for branch-related actions.
    """

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.can_add_%(model_name)s_branch"],
        "PUT": ["%(app_label)s.can_change_%(model_name)s_branch"],
        "PATCH": ["%(app_label)s.can_change_%(model_name)s_branch"],
        "DELETE": ["%(app_label)s.can_delete_%(model_name)s_branch"],
    }

    def get_binding_object(self, request):
        """
        This method is used to get the binding object for the permission check.
        It can be overridden in subclasses to provide custom logic.
        """
        return request.branch if hasattr(request, "branch") else None

    def _resolve_branch(self, request):
        """Try to identify the target Branch for a POST request.

        Looks in (in order): existing ``request.branch`` from middleware, then
        ``branch`` / ``branch_id`` in the body. Returns ``None`` if no branch
        can be located.
        """
        branch = getattr(request, "branch", None)
        if branch:
            return branch

        branch_id = request.data.get("branch") or request.data.get("branch_id")
        if not branch_id:
            return None
        branch = Branch.objects.filter(id=branch_id).first()
        if branch:
            # Backfill so downstream view code can rely on it
            request.branch = branch
            if not getattr(request, "business", None):
                request.business = branch.business
        return branch

    def _resolve_business(self, request):
        """Locate the target business from request context or body."""
        business = getattr(request, "business", None)
        if business:
            return business
        business_id = request.data.get("business") or request.data.get("business_id")
        if not business_id:
            return None
        business = Business.objects.filter(id=business_id).first()
        if business:
            request.business = business
        return business

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        if request.method != "POST":
            # GET / list and detail mutations are handled by get_queryset and
            # has_object_permission respectively.
            return True

        model_cls = view.queryset.model
        perms = self.get_required_object_permissions(request.method, model_cls)

        # Prefer the explicit branch when supplied; this is the strongest signal
        # of where the new object will live.
        branch = self._resolve_branch(request)
        if branch:
            return request.user.has_perms(perms, branch)

        # Fall back to "user must hold the branch perm on at least one branch
        # within the targeted business". This makes endpoints usable when the
        # caller only supplies ``business_id`` and the serializer infers the
        # branch later (e.g. inventory movements).
        business = self._resolve_business(request)
        if not business:
            # No branch and no business context: defer to object-level checks /
            # view's own validation logic.
            return True
        return any(
            request.user.has_perms(perms, branch_obj)
            for branch_obj in business.branches.all()
        )

    def _branches_for_obj(self, obj):
        """Return the ``Branch`` instances tied to ``obj`` for perm checks.

        Looks at common attributes used across this codebase:
        ``branch`` (most models), ``from_branch`` / ``to_branch``
        (inventory movements), or the branch on a related supply / item.
        """
        branches = []
        for attr in ("branch", "from_branch", "to_branch"):
            value = getattr(obj, attr, None)
            if value is not None:
                branches.append(value)
        if not branches:
            for related_attr in ("supply", "item"):
                related = getattr(obj, related_attr, None)
                related_branch = getattr(related, "branch", None) if related else None
                if related_branch is not None:
                    branches.append(related_branch)
        return branches

    def has_object_permission(self, request, view, obj):
        queryset = self._queryset(view)
        model_cls = queryset.model
        user = request.user
        perms = self.get_required_object_permissions(request.method, model_cls)

        # Prefer the branch from the middleware when the caller supplied one,
        # otherwise look at the object itself. Custom actions (e.g.
        # ``/movements/{id}/approve/``) typically arrive without query params.
        targets = []
        binding = self.get_binding_object(request)
        if binding is not None:
            targets.append(binding)
        targets.extend(self._branches_for_obj(obj))

        if any(user.has_perms(perms, target) for target in targets if target):
            return True

        if request.method in SAFE_METHODS:
            raise Http404

        # Determine if the user has read access to the object — if not, mask
        # the existence of the resource by raising 404 instead of 403.
        read_perms = self.get_required_object_permissions("GET", model_cls)
        if read_perms and not any(
            user.has_perms(read_perms, target) for target in targets if target
        ):
            raise Http404

        return False


class GuardianObjectPermissions(BasePermission):
    """
    Custom permission class that properly works with django-guardian for object-level permissions.
    Based on DjangoObjectPermissions but adapted for Guardian.
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        kwargs = {
            "app_label": model_cls._meta.app_label,
            "model_name": model_cls._meta.model_name,
        }

        if method not in self.perms_map:
            return []

        return [perm % kwargs for perm in self.perms_map[method]]

    def has_permission(self, request, view):
        """
        Check if user is authenticated.
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions using django-guardian.
        """
        queryset = self._queryset(view)
        model_cls = queryset.model
        user = request.user
        perms = self.get_required_permissions(request.method, model_cls)

        # Check if user has the required permissions on this specific object
        if not user.has_perms(perms, obj):
            return False

        return True

    def _queryset(self, view):
        """
        Get the queryset from the view.
        """
        if hasattr(view, "get_queryset"):
            queryset = view.get_queryset()
            if queryset is not None:
                return queryset

        if hasattr(view, "queryset") and view.queryset is not None:
            return view.queryset

        raise AssertionError(
            f"Cannot apply {self.__class__.__name__} on a view that "
            f"does not set `.queryset` or have a `.get_queryset()` method."
        )
