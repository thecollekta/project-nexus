from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import CurrencyField

from apps.accounts.managers import ActiveManager, UserManager
from apps.core.models import AllObjectsManager, AuditStampedModelBase


# Custom managers for specific user queries
class CustomerManager(ActiveManager):
    """Manager for customer users only."""

    def get_queryset(self):
        return super().get_queryset().filter(user_type=User.UserType.CUSTOMER)


class AdminUserManager(ActiveManager):
    """Manager for admin users only."""

    def get_queryset(self):
        return super().get_queryset().filter(user_type=User.UserType.ADMIN)


class User(AuditStampedModelBase, AbstractUser):
    """
    Custom User model that extends Django's AbstractUser.
    Includes additional fields for e-commerce functionality and audit trail.
    """

    class UserType(models.TextChoices):
        CUSTOMER = "CUSTOMER", _("Customer")
        ADMIN = "ADMIN", _("Admin")
        STAFF = "STAFF", _("Staff")

    class StatusType(models.TextChoices):
        ACTIVE = "active", _("Active")
        SUSPENDED = "suspended", _("Suspended")
        PENDING = "pending", _("Pending Verification")

    # User fields
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    email_verified = models.BooleanField(
        _("email verified"),
        default=False,
        help_text=_("Designates whether this user's email has been verified."),
    )
    email_verification_token = models.CharField(
        _("email verification token"),
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
    )
    email_verification_token_created_at = models.DateTimeField(
        _("verification token created at"),
        blank=True,
        null=True,
    )
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_("Not used for login. Only for internal reference."),
        blank=True,
        null=True,
    )
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.CUSTOMER,
        help_text=_("The type of user role"),
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Phone number must be entered in the format: '+233123456'. Up to 15 digits allowed.",
            ),
        ],
        help_text=_("Contact phone number"),
    )

    # Address fields
    address_line_1 = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Primary address line"),
    )
    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Secondary address line (apartment, suite, etc.)"),
    )
    city = models.CharField(max_length=100, blank=True, help_text=_("City"))
    state = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Region/State/Province"),
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Postal or ZIP code"),
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        default="Ghana",
        help_text=_("Country"),
    )

    # Account status
    account_status = models.CharField(
        max_length=20,
        choices=StatusType.choices,
        default=StatusType.PENDING,
        help_text=_("Current account status"),
    )

    # Use email as the username field for authentication
    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = ["username", "first_name", "last_name"]

    # Managers
    objects = UserManager()  # Default manager with create_user and create_superuser
    active = ActiveManager()  # Only returns active users
    all_objects = AllObjectsManager()  # Returns all users including inactive
    customers = CustomerManager()  # Manager for customer users
    admin_users = AdminUserManager()  # Manager for admin users

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering: ClassVar[list[str]] = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_address(self):
        """Return the formatted full address."""
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
        ]
        return ", ".join([part for part in address_parts if part])

    def is_customer(self):
        """Check if user is a customer."""
        return self.user_type == self.UserType.CUSTOMER

    def is_admin_user(self):
        """Check if user is an admin (different from Django's is_superuser)."""
        return self.user_type == self.UserType.ADMIN or self.is_superuser

    def activate_account(self):
        """Activate the user account."""
        self.account_status = self.StatusType.ACTIVE
        self.email_verified = True
        self.is_active = True
        self.save(
            update_fields=[
                "account_status",
                "email_verified",
                "is_active",
                "updated_at",
            ],
        )

    def suspend_account(self):
        """Suspend the user account."""
        self.account_status = self.StatusType.SUSPENDED
        self.is_active = False
        self.save(update_fields=["account_status", "is_active", "updated_at"])

    def verify_email(self, token):
        """
        Verify the user's email using the provided token.
        Returns True if verification was successful, False otherwise.
        """
        if not self.email_verification_token or self.email_verification_token != token:
            return False

        # Check if token is expired (24 hours)
        if (
            self.email_verification_token_created_at
            and timezone.now()
            > self.email_verification_token_created_at + timezone.timedelta(days=1)
        ):
            return False

        self.email_verified = True
        self.email_verification_token = None
        self.email_verification_token_created_at = None
        self.save(
            update_fields=[
                "email_verified",
                "email_verification_token",
                "email_verification_token_created_at",
            ],
        )
        return True

    def generate_email_verification_token(self):
        """Generate a new email verification token."""
        self.email_verification_token = get_random_string(64)
        self.email_verification_token_created_at = timezone.now()
        self.save(
            update_fields=[
                "email_verification_token",
                "email_verification_token_created_at",
            ],
        )
        return self.email_verification_token


class UserProfile(AuditStampedModelBase):
    """
    Extended profile information for users.
    Separate model to keep User model focused on authentication.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    preferred_currency = CurrencyField(
        default="GHS", help_text=_("User's preferred currency")
    )

    # Profile image
    avatar = models.ImageField(
        upload_to="user_avatars/",
        blank=True,
        null=True,
        help_text=_("User profile picture"),
    )

    # Additional profile fields
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text=_("Date of birth"),
    )

    bio = models.TextField(max_length=500, blank=True, help_text=_("Short biography"))

    # Preferences
    newsletter_subscription = models.BooleanField(
        default=False,
        help_text=_("Subscribe to newsletter"),
    )

    marketing_emails = models.BooleanField(
        default=False,
        help_text=_("Receive marketing emails"),
    )

    # Social media links
    website = models.URLField(blank=True, help_text=_("Personal website"))

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile when a User is created.
    """
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the UserProfile when the User is saved.
    """
    if hasattr(instance, "profile"):
        instance.profile.save()
