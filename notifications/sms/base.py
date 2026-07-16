from abc import ABC, abstractmethod


class BaseSmsBackend(ABC):
    """Base class for pluggable SMS backends.

    Set ``settings.SMS_BACKEND`` to the dotted path of a subclass (see
    ``notifications.sms.backends``) to select a provider — same idea as
    Django's built-in ``EMAIL_BACKEND`` setting. Call sites never import a
    concrete backend directly; they call ``notifications.sms.send_sms()``.
    """

    @abstractmethod
    def send(self, phone_number: str, message: str) -> bool:
        """Send ``message`` to ``phone_number``.

        ``phone_number`` is in the app's local storage form (e.g.
        ``"911639555"`` — no country code, see ``User.normalize_phone``).
        Backends are responsible for reformatting it however their provider
        expects (e.g. a 251-prefixed MSISDN).

        Returns True on success, False on failure. Should not raise for
        ordinary delivery failures (network/provider errors) so a failed
        SMS never breaks the caller's flow (e.g. registration) — only
        programmer/config errors should propagate.
        """
