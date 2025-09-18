# apps/accounts/tokens.py

"""
Token generators for user account management.
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import six  # type: ignore


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Strategy object used to generate and check tokens for email verification.
    """

    def _make_hash_value(self, user, timestamp):
        """
        Hash the user's primary key, email verification status, and some user state
        that's sure to change after a password reset to produce a token that is
        invalidated when it's used.

        Args:
            user: User instance
            timestamp: Timestamp when the token was generated

        Returns:
            str: Hash value for the token
        """
        # Ensure the token is invalidated when the user changes their password
        login_timestamp = (
            ""
            if user.last_login is None
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        return (
            six.text_type(user.pk)
            + six.text_type(user.email_verified)  # type: ignore
            + six.text_type(login_timestamp)
            + six.text_type(timestamp)
        )


# Create an instance of the token generator
email_verification_token = EmailVerificationTokenGenerator()
