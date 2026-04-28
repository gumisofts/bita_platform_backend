# Changelog

All notable changes to the Bita Platform Backend project are documented in this
file. The format is loosely based on [Keep a Changelog](https://keepachangelog.com/),
and the project does not yet follow Semantic Versioning strictly.

See [`BUGFIXES.md`](./BUGFIXES.md) for the engineering rationale and reproduction
steps behind each fix.

## [Unreleased] – 2026-04-28 — Bug-fix & hardening sweep

### Security

- **accounts**: `verify_google_id_token` now passes `settings.GOOGLE_WEB_CLIENT_ID`
  as the audience and rejects tokens whose `iss` claim is not Google's. The
  previous implementation accepted any valid Google-signed token, which would
  have allowed an attacker with a token issued for a *different* OAuth client
  to log into Bita. (`accounts/utils.py`)
- **accounts**: SMS/email verification codes are no longer hardcoded to
  `"123456"` in `RegisterSerializer`, `SendVerificationCodeSerializer`,
  `PhoneChangeRequestSerializer`, `EmailChangeRequestSerializer`,
  `ResetPasswordRequestSerializer`, and `ConfirmDeleteUserDeleteView.send_delete_user_code`.
  All call sites now use `accounts.utils.generate_secure_six_digits()` and
  store the **hashed** code via `VerificationCode.save()` /
  `make_password()`. (`accounts/serializers.py`, `accounts/views.py`)
- **accounts**: `VerificationCode.save()` previously only hashed the code when
  callers explicitly passed `force_insert=True`; `QuerySet.create()` and most
  `save()` calls left codes in plaintext in the database. The model now hashes
  on first insert whenever the value isn't already a Django password hash, and
  the leftover `print(args)` / `print(kwargs)` debug statements were removed.
  (`accounts/models.py`)
- **accounts**: `PasswordChangeSerializer` re-use detection is now correct.
  The previous filter compared the new password's *salted* hash against stored
  hashes — and salts are random, so the lookup always returned `None` and the
  re-use check never fired. The new code iterates the user's password history
  and uses the constant-time `check_password`. The previous password is also
  now persisted to `Password` so future re-use checks have data to consult.
  (`accounts/serializers.py`)
- **accounts**: JWT access tokens defaulted to **90 days** of validity, which
  effectively turned them into long-lived bearer credentials. The default is
  now **60 minutes** with a 30-day refresh token (override via
  `DJANGO_JWT_ACCESS_MINUTES` / `DJANGO_JWT_REFRESH_DAYS`), and refresh tokens
  rotate on use. (`core/settings.py`)
- **crms**: `CustomerViewSet`, `GiftCardViewSet`, and `GiftCardTransferViewSet`
  had `permission_classes = []`, which let any unauthenticated user list,
  create, update, or delete customer / gift-card data. They now require
  authentication and the same business / branch object-level permission stack
  used by the rest of the platform. (`crms/views.py`)
- **business**: `BusinessModelObjectPermission.has_object_permission` was
  missing the `obj` positional argument that DRF passes — every detail-level
  permission check raised `TypeError` and was effectively bypassed (DRF treats
  the exception as "no permission" or surfaces a 500 depending on the view).
  The signature now matches DRF's contract. (`business/permissions.py`)

### Fixed (NameErrors / runtime crashes)

- **accounts/views.py**: imports `RefreshToken`, `timedelta`, `make_password`,
  `check_password`, and `generate_secure_six_digits`. The
  `ConfirmDeleteUserDeleteView.verify_code` and `send_delete_user_code` actions
  raised `NameError` on every request because none of these symbols were
  imported.
- **accounts/views.py**: `get_user_detail`, `verify_code`, and
  `send_delete_user_code` initialised `user = None` before the email/phone
  branches and use `if not user and …` to fall through. The previous code
  raised `NameError: name 'user' is not defined` whenever `email` was missing.
  The misleading "Email and phone number cannot be used together" message
  (which actually triggered when *neither* was given) was rewritten.
- **accounts/serializers.py**: `ConfirmResetPasswordRequestViewsetSerializer.validate`
  used `attrs.key()` (typo for `keys()`) inside the "no user found" branch,
  raising `AttributeError` whenever a reset-password request hit that path.
- **accounts/serializers.py**: `SendVerificationCodeSerializer.validate`
  passed a generator expression as the *first positional argument* to
  `ValidationError`, which DRF then attempted to render as a dict and crashed
  with a confusing serialization error. The error payload is now a proper
  `dict` and the missing-identifier guard is hoisted up.
- **accounts/serializers.py**: removed the duplicate `PhoneChangeRequestSerializer`
  declaration. The first definition (built around the legacy `requests.post(...)`
  notification API) silently shadowed the model-backed version meant to be
  used by the API.
- **inventories/views.py**: `InventoryMovementViewSet.get_queryset` referenced
  `models.Q(...)` without importing `models`. Switched to the already-imported
  `Q` symbol so the queryset filter works.
- **orders/views.py**: `OrderItemViewset.create` looked up
  `SuppliedItem.objects.filter(item=order_item.item).order_by("-timestamp")`
  but `OrderItem` has no `item` attribute (it points at `ItemVariant`) and
  `SuppliedItem` has no `timestamp` field. Rewritten to filter by
  `variant=order_item.variant` and order by `-created_at`, and to read the
  unit price from `selling_price` (the only price column that actually exists
  on `SuppliedItem`).
- **inventories/signals.py**: `on_supplied_item_deleted` recomputed the
  variant's selling price with
  `Q(variant=instance.variant, quantity__gt=0) & ~Q(variant_id=instance.variant.id)`,
  which is contradictory — the same row can't both match and not match the
  variant filter. The aggregate therefore *always* returned `None` and reset
  the variant's `selling_price` to `NULL` on every supplied-item delete.
  Replaced with `…filter(variant=…).exclude(pk=instance.pk)` so the price now
  correctly falls back to the next-highest in-stock supply.

### Fixed (data integrity / behavioural)

- **core/settings.py**: `DJANGO_DEBUG` parsing accepted only the literal
  string `"True"`. It now accepts `True/true/1/yes` (case-insensitive) and
  defaults to `False`.
- **core/settings.py**: `urlparse(os.getenv("DJANGO_POSTGRES_URL"))` raised
  `TypeError: argument of type 'NoneType' is not iterable` when the env var
  was unset, breaking `manage.py` for first-time clones. Settings now fall
  back to a local SQLite DB when no Postgres URL is configured and use a
  sensible `CONN_MAX_AGE = 60` instead of the invalid `None`.
- **core/settings.py**: `TEMPLATES["DIRS"]` pointed at `"notification.templates"`
  (missing trailing `s`, dot path instead of filesystem path) which Django
  silently ignored. Set to `BASE_DIR / "notifications" / "templates"` so the
  packaged Swagger/Redoc landing page actually loads.
- **core/settings.py**: removed a duplicate `CORS_ALLOWED_ORIGINS` assignment.
- **business/middleware.py**: removed two bare `except:` blocks that swallowed
  every exception (including `KeyboardInterrupt` and `SystemExit`). The
  middleware now also accepts `X-Business-Id` / `X-Branch-Id` headers as a
  fallback for `POST` requests that previously couldn't carry the context
  (since `request.GET` is empty), validates ids with `is_valid_uuid` before
  hitting the DB, and back-fills `request.business` from `request.branch`
  when only the branch was supplied.
- **core/utils.py**: `is_valid_uuid(value)` raised `AttributeError` whenever
  `value` was not a string and rejected uppercase UUIDs because of the
  `str(val) == value.lower()` comparison. Now returns `True` for any value
  that `uuid.UUID(...)` can parse, regardless of case or input type.
- **orders/serializers.py**: `OrderSerializer.validate` had a leftover
  `print(attrs)`, dead code after `return super().validate(attrs)`, and an
  unsafe `variant.item.branch != branch` comparison (works on objects, but
  fails when one side is `None`). Cleaned up and switched to comparing
  `branch_id` directly to avoid the lazy-load.

### Tooling / DevX

- **JWT**: introduced `DJANGO_JWT_ACCESS_MINUTES` and `DJANGO_JWT_REFRESH_DAYS`
  env knobs so each deployment can tune token lifetimes without code changes.

### Manual follow-ups required

These changes need to be performed by an operator and were not done by this
patch:

1. **Rotate AWS credentials.** The previously committed local `.env` (now
   gitignored, untracked) contained live `AWS_ACCESS_KEY_ID` /
   `AWS_SECRET_ACCESS_KEY` values for `eu-north-1` and a real
   `DJANGO_SECRET_KEY`. Even though the file isn't in the git history (only
   `.env.example` is tracked), assume the values have been seen and rotate
   them in IAM and re-issue a new Django SECRET_KEY.
2. **Plumb the verification-code dispatcher.** Several call sites that
   previously stored `"123456"` now generate cryptographically-secure codes
   but still leave a `TODO` for delivering them via the SMS / email
   notification service. Wire those up to the existing notification stack
   before shipping account-deletion / password-reset / phone-change UX.

### Test status

`python manage.py test --keepdb` — **90/90 passing** after the changes
(`Ran 90 tests in 77.6s`).
