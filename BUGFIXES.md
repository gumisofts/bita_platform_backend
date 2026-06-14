# Bug-fix audit — 2026-04-28

This document expands on each entry in [`CHANGELOG.md`](./CHANGELOG.md) with
the original code, the symptom, the root cause, and the fix. It is intended
both as a justification for the patch and as a catalogue of patterns to avoid
in future PRs.

---

## 1. Critical security: Google OAuth audience not validated

**Where:** `accounts/utils.py — verify_google_id_token`
**Severity:** Critical (authentication bypass risk)

The original implementation called `id_token.verify_oauth2_token(token, requests.Request())`
with no `audience` argument. Google's library accepts that, but it then only
checks the token's signature and expiry — it does **not** check that the token
was minted for the Bita web client. That means any valid Google ID token,
including one issued for a completely unrelated OAuth client, would authenticate
through `/accounts/auth/google/login`.

The fix passes `settings.GOOGLE_WEB_CLIENT_ID` as the audience and additionally
asserts the `iss` claim is one of Google's two canonical issuers. When
`GOOGLE_WEB_CLIENT_ID` is not configured we keep the legacy behaviour but log
a loud warning so it shows up in observability.

---

## 2. Critical security: hardcoded `123456` verification codes

**Where:**

- `accounts/serializers.py` — `RegisterSerializer.create`
- `accounts/serializers.py` — `SendVerificationCodeSerializer.create`
- `accounts/serializers.py` — `PhoneChangeRequestSerializer.create`
- `accounts/serializers.py` — `EmailChangeRequestSerializer.create`
- `accounts/serializers.py` — `ResetPasswordRequestSerializer.validate`
- `accounts/views.py` — `ConfirmDeleteUserDeleteView.send_delete_user_code`

**Severity:** Critical (account takeover via deterministic OTP)

Every code path that issues an OTP — registration, resend-verification,
phone change, email change, password reset, and account-deletion — was
storing the literal string `"123456"` as the verification code. The
"TODO change this on production" comment had been there long enough to be
forgotten. With a known code, anyone who knew a target's email or phone
could complete every flow guarded by these OTPs.

The fix wires every site to `accounts.utils.generate_secure_six_digits()`
(which uses `secrets.randbelow`) and ensures the value is hashed before it
hits the database (see also #3).

---

## 3. Critical security: VerificationCode never hashed via `objects.create`

**Where:** `accounts/models.py — VerificationCode.save`

```python
def save(self, force_insert=False, *args, **kwargs):
    print(kwargs)
    print(args)
    if force_insert:
        self.code = make_password(self.code)
    return super().save(force_insert=force_insert, *args, **kwargs)
```

`QuerySet.create()` and bare `instance.save()` calls never pass
`force_insert=True`, so the `if force_insert:` branch was almost never taken.
Verification codes were therefore stored in **plaintext** in the
`accounts_verificationcode.code` column. Any DB read access (replicated
backups, support tools, the admin) leaked OTPs.

The fix:

- Removes the `print` statements.
- Drops the misleading `force_insert` parameter from the signature.
- Uses `self._state.adding` plus `is_password_usable(self.code)` to hash
  the code on first insert idempotently. Subsequent saves (e.g. flipping
  `is_used=True`) leave the existing hash alone.

---

## 4. Critical security: password re-use detection broken

**Where:** `accounts/serializers.py — PasswordChangeSerializer.validate`

```python
password = (
    Password.objects.filter(
        password=Password.hash_password(attrs.get("new_password"))
    )
    .order_by("created_at")
    .first()
)
```

`make_password()` (and therefore `Password.hash_password()`) generates a fresh
random salt on every call, so two hashes of the same plaintext are never
byte-equal. The filter could therefore *never* match anything and the
"you cannot use one of your old passwords as new password" guard never fired.
Even worse, the code that *would* have populated `Password` for future
look-ups was commented out, so the table is empty in practice.

The fix iterates over the user's password history and uses
`django.contrib.auth.hashers.check_password` (constant-time and salt-aware)
to detect re-use. The serializer's `create()` now persists the user's
previous hash to `Password` so the history actually accumulates.

---

## 5. Critical security: customer / gift-card endpoints unauthenticated

**Where:** `crms/views.py`

```python
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = []
```

`permission_classes = []` is **not** "use the global default" — it's "allow
everyone, including anonymous users". The same was true for `GiftCardViewSet`
and `GiftCardTransferViewSet`. Anyone on the internet could have listed,
created, modified, and deleted PII (full name, phone, email) and gift-card
balances by hitting `/crms/customers/`.

All three viewsets now require `IsAuthenticated` and the platform's standard
business / branch object permission stack.

---

## 6. Critical security: `BusinessModelObjectPermission.has_object_permission` signature

**Where:** `business/permissions.py`

```python
def has_object_permission(self, request, view):  # missing `obj`
    return has_business_object_permission(...)
```

DRF calls `permission.has_object_permission(request, view, obj)`. The missing
parameter means every detail-level permission check on a viewset using this
class raised `TypeError: has_object_permission() takes 3 positional arguments
but 4 were given`. Depending on where the check fired, this either bubbled up
as a 500 (effectively denying access) or — worse — was caught by another
`except Exception` block and silently allowed the request through.

The fix accepts `obj` to match DRF's contract.

---

## 7. JWT lifetime — 90 days is not a session token

**Where:** `core/settings.py`

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=90),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=90),
    ...
}
```

A 90-day access token effectively turns into a long-lived bearer credential.
Combined with the lack of refresh-token rotation, a single leaked token gave
attackers three months of access. The new defaults are 60-minute access
tokens, 30-day refresh tokens, and `ROTATE_REFRESH_TOKENS = True`. Operators
can override per environment via `DJANGO_JWT_ACCESS_MINUTES` and
`DJANGO_JWT_REFRESH_DAYS`.

---

## 8. NameError on `RefreshToken` and `timedelta` in account-deletion flow

**Where:** `accounts/views.py — ConfirmDeleteUserDeleteView`

The actions referenced `RefreshToken.for_user(user)` and
`timezone.now() + timedelta(minutes=5)` without importing either. Every call
to `verify-code` or `send-code` therefore raised `NameError` and 500'd. The
imports are now present, and the action also uses
`generate_secure_six_digits()` + `make_password()` instead of `"123456"`
plaintext.

---

## 9. NameError: `models.Q` in inventory movement filtering

**Where:** `inventories/views.py — InventoryMovementViewSet.get_queryset`

```python
queryset = queryset.filter(
    models.Q(from_branch_id=branch_id) | models.Q(to_branch_id=branch_id)
)
```

`models` was never imported. Switched to the already-imported `Q` from
`django.db.models`.

---

## 10. NameError on `user` when only one identifier is supplied

**Where:** `accounts/views.py — ConfirmDeleteUserDeleteView.{get_user_detail, verify_code, send_delete_user_code}`

```python
if email:
    user = User.objects.filter(email=email).first()
if phone_number:
    user = User.objects.filter(phone_number=phone_number).first()
if not user:
    return Response(...)
```

If the caller only sent `phone_number` the first `if` is skipped and `user`
is undefined; then `if not user:` raises `NameError`. The misleading
`"Email and phone number cannot be used together"` error message was actually
returned when *neither* was supplied. Fixed by initialising `user = None`,
swapping the second `if` to `elif not user`, and rewording the validation
message.

---

## 11. AttributeError in password-reset confirm

**Where:** `accounts/serializers.py — ConfirmResetPasswordRequestViewsetSerializer.validate`

```python
raise ValidationError(
    {key: [f"no user found with the given {key}"] for key in attrs.key()},
    400,
)
```

`attrs.key()` is a typo — `dict` has `.keys()`, not `.key()`. The bug only
fires when no user matches the supplied identifier, which is exactly the path
that needs to behave well for callers. Now spells `keys()`.

---

## 12. Malformed `ValidationError` in `SendVerificationCodeSerializer`

**Where:** `accounts/serializers.py`

```python
raise ValidationError(
    {key: [f"no unverified user with this {key}"]} for key in attrs
)
```

Note the missing surrounding `{ }` — this passes a *generator expression* of
single-key dicts as the `detail` argument, instead of a dict comprehension.
DRF couldn't render it consistently. Replaced with a real dict
comprehension and added an upstream check that at least one identifier
(email or phone_number) was supplied so we never iterate an empty `attrs`.

---

## 13. Duplicate `PhoneChangeRequestSerializer`

**Where:** `accounts/serializers.py`

The file defined two classes with the same name. In Python the second
definition wins, so the first version (which fired off an HTTP POST to a
notification microservice) was dead code, and a careful reader believing
it was the active class could be misled. Removed the obsolete definition.

---

## 14. `OrderItemViewset.create` accessed non-existent fields

**Where:** `orders/views.py`

```python
latest_supply = (
    SuppliedItem.objects.filter(item=order_item.item)  # OrderItem has .variant, not .item
    .order_by("-timestamp")                            # SuppliedItem has no `timestamp` field
    .first()
)
...
item_unit_price = latest_supply.price                  # SuppliedItem has `selling_price`, not `price`
```

Three field references that don't exist. The first call into this endpoint
would have crashed with `AttributeError`. The fix walks `order_item.variant`,
orders by `-created_at` (the BaseModel timestamp), and reads `selling_price`.
We also guard the `+=` with a `Decimal("0")` fallback in case `total_payable`
is `None`.

---

## 15. Wrong queryset in `on_supplied_item_deleted` price recalculation

**Where:** `inventories/signals.py`

```python
max_price = SuppliedItem.objects.filter(
    Q(variant=instance.variant, quantity__gt=0) & ~Q(variant_id=instance.variant.id)
).aggregate(max_selling_price=Max("selling_price"))["max_selling_price"]
```

`Q(variant=instance.variant) & ~Q(variant_id=instance.variant.id)` is an
empty set — the same row can't both match and not match the variant filter.
`max_price` was therefore *always* `None`, and every delete blanked the
variant's `selling_price` to `NULL`. The fix excludes by `pk=instance.pk`
so the aggregate considers the *other* in-stock supplies for the same
variant.

---

## 16. Settings: TEMPLATES pointing at a path that doesn't exist

**Where:** `core/settings.py`

```python
"DIRS": ["notification.templates"],
```

`notification.templates` is neither a filesystem path nor a real importable
module — Django silently ignored it and never found `templates/index.html`.
Set to `BASE_DIR / "notifications" / "templates"`.

---

## 17. Settings: `DJANGO_DEBUG` parser brittle, duplicate CORS, NoneType crash

**Where:** `core/settings.py`

- `DEBUG = os.getenv("DJANGO_DEBUG", False) == "True"` worked, but only when
  the variable contained the exact string `"True"`. `1`, `true`, and `yes`
  were silently treated as production. Now parses case-insensitively against
  `{"true", "1", "yes"}`.
- `CORS_ALLOWED_ORIGINS` was assigned twice in the same file with the same
  value. The duplicate was removed.
- `urlparse(os.getenv("DJANGO_POSTGRES_URL"))` raised `TypeError` when the
  env var was unset, which broke clean clones (`manage.py check`,
  `manage.py migrate` could not import settings). Settings now fall back to
  SQLite when no Postgres URL is configured. `CONN_MAX_AGE` was changed from
  the invalid `None` to `60` so persistent connections actually work.

---

## 18. Middleware: bare except, no support for header-based context

**Where:** `business/middleware.py`

```python
try:
    request.business = Business.objects.get(id=business_id)
except:
    request.business = None
```

Bare `except:` swallows `KeyboardInterrupt`, `SystemExit`, and other
unrelated errors. The middleware also only inspected `request.GET`, so
POST/PUT requests (where the body holds the business id) had no way to
populate `request.business`. The rewrite:

- Catches `Business.DoesNotExist` explicitly, plus a defensive `Exception`
  branch that logs at `WARNING`.
- Adds `X-Business-Id` / `X-Branch-Id` request-header fallbacks for clients
  that can't put the id in the URL.
- Validates ids with `is_valid_uuid` before hitting the DB to avoid wasted
  queries on garbage input.
- Back-fills `request.business` from `request.branch` when only the branch
  was specified.

---

## 19. `core/utils.is_valid_uuid` rejects valid UUIDs

**Where:** `core/utils.py`

```python
def is_valid_uuid(value):
    try:
        val = uuid.UUID(str(value))
        return str(val) == value.lower()
    except ValueError:
        return False
```

Two issues:

1. `value.lower()` raises `AttributeError` if `value` is not a string (e.g.
   already a `UUID` object or an integer).
2. `str(val)` is always lowercase, so the comparison rejected uppercased UUIDs
   even though they parse fine.

The check now returns `True` for any value `uuid.UUID(...)` accepts.

---

## 20. `OrderSerializer.validate` had debug print + dead code

**Where:** `orders/serializers.py`

```python
print(attrs)
...
return super().validate(attrs)

return attrs   # dead code, unreachable
```

Cleaned up the `print`, removed the unreachable `return`, switched to
`branch_id == branch.id` for the per-variant branch check (avoids spurious
DB hits via lazy loading on `variant.item.branch`), and added a `None`
guard for variants.

---

## Manual follow-ups (not done in this patch)

1. **Rotate AWS credentials and Django `SECRET_KEY`.** The local `.env`
   (gitignored, untracked) carried live AWS keys and a real Django
   `SECRET_KEY`. Even though they aren't in the git history, treat them as
   compromised and rotate.
2. **Wire up the OTP dispatcher.** Every serializer that previously stored
   `"123456"` now generates a cryptographically-secure code, but the actual
   send-via-SMS / send-via-email step is still a `TODO`. Hook these into the
   existing notifications pipeline before relying on them in production.
3. **Audit other apps for the patterns fixed here.** The same anti-patterns
   (`bare except`, undefined `user` variable, `permission_classes = []`,
   `print(...)` debug calls, unreachable `return`) likely exist elsewhere.
   Worth a follow-up sweep over `markets/`, `chat/`, `finances/`, and
   `administration/`.
