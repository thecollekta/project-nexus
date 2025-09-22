# apps/accounts/admin.py

"""
Django admin configuration for user management.
Provides a comprehensive interface for managing users and their profiles.
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.html import format_html

from apps.accounts.models import User, UserProfile
from apps.accounts.tasks import send_welcome_email_task


class CustomUserCreationForm(UserCreationForm):
    """
    Custom user creation form for the admin.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "user_type")


class CustomUserChangeForm(UserChangeForm):
    """
    Custom user change form for the admin.
    """

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


class UserProfileInline(admin.StackedInline):
    """
    Inline admin for UserProfile model.
    Allows editing profile within the User admin page.
    """

    model = UserProfile
    fk_name = "user"
    can_delete = False
    verbose_name_plural = "Profile Information"
    extra = 0

    fieldsets = (
        ("Personal Information", {"fields": ("date_of_birth", "bio")}),
        ("Preferences", {"fields": ("newsletter_subscription", "marketing_emails")}),
        ("Social Links", {"fields": ("website",), "classes": ("collapse",)}),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model.
    Extends Django's built-in UserAdmin with additional functionality.
    """

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    inlines = [UserProfileInline]

    # List display configuration
    list_display = (
        "username",
        "email",
        "full_name",
        "user_type",
        "account_status_display",
        "email_verified_display",
        "is_active",
        "date_joined_display",
        "last_login_display",
    )

    list_filter = (
        "user_type",
        "account_status",
        "email_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone_number",
    )

    ordering = ("-date_joined",)

    # Fieldsets for the change form
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal Info",
            {"fields": ("first_name", "last_name", "email", "phone_number")},
        ),
        (
            "Address Information",
            {
                "fields": (
                    "address_line_1",
                    "address_line_2",
                    "city",
                    "state",
                    "postal_code",
                    "country",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Account Settings",
            {
                "fields": (
                    "user_type",
                    "account_status",
                    "email_verified",
                    "email_verification_token",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Important Dates",
            {"fields": ("last_login", "date_joined"), "classes": ("collapse",)},
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    # Fieldsets for the add form
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "user_type",
                    "first_name",
                    "last_name",
                ),
            },
        ),
    )

    readonly_fields = (
        "date_joined",
        "last_login",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "id",
    )

    # Custom display methods
    def account_status_display(self, obj):
        """Display account status with color coding."""
        colors = {
            "active": "green",
            "suspended": "red",
            "pending": "orange",
        }
        color = colors.get(obj.account_status, "black")
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_account_status_display(),
        )

    account_status_display.short_description = "Account Status"
    account_status_display.admin_order_field = "account_status"

    def email_verified_display(self, obj):
        """Display email verification status with icons."""
        if obj.email_verified:
            return format_html('<span style="color: green;">Verified</span>')
        else:
            return format_html('<span style="color: red;">Not Verified</span>')

    email_verified_display.short_description = "Email Status"
    email_verified_display.admin_order_field = "email_verified"

    def date_joined_display(self, obj):
        """Display formatted join date."""
        return obj.date_joined.strftime("%Y-%m-%d %H:%M")

    date_joined_display.short_description = "Joined"
    date_joined_display.admin_order_field = "date_joined"

    def last_login_display(self, obj):
        """Display formatted last login date."""
        if obj.last_login:
            return obj.last_login.strftime("%Y-%m-%d %H:%M")
        return "Never"

    last_login_display.short_description = "Last Login"
    last_login_display.admin_order_field = "last_login"

    # Custom actions
    actions = [
        "activate_users",
        "suspend_users",
        "verify_emails",
        "send_welcome_emails",
    ]

    def activate_users(self, request, queryset):
        """Bulk activate selected users."""
        count = 0
        for user in queryset:
            if user.account_status != "active":
                user.activate_account()
                count += 1

        self.message_user(request, f"{count} user(s) have been activated successfully.")

    activate_users.short_description = "Activate selected users"

    def suspend_users(self, request, queryset):
        """Bulk suspend selected users."""
        # Prevent suspending superusers or the current user
        valid_users = queryset.exclude(id=request.user.id).exclude(is_superuser=True)

        count = 0
        for user in valid_users:
            if user.account_status != "suspended":
                user.suspend_account()
                count += 1

        self.message_user(request, f"{count} user(s) have been suspended successfully.")

    suspend_users.short_description = "Suspend selected users"

    def verify_emails(self, request, queryset):
        """Bulk verify email addresses."""
        count = queryset.filter(email_verified=False).update(
            email_verified=True, email_verification_token=""
        )

        self.message_user(request, f"{count} email(s) have been verified successfully.")

    verify_emails.short_description = "Verify selected user emails"

    def send_welcome_emails(self, request, queryset):
        """Send welcome emails to selected users asynchronously."""
        count = 0
        for user in queryset:
            if user.is_active and user.email:
                send_welcome_email_task.delay(user.id)
                count += 1

        if count == 1:
            message = "1 welcome email has been queued for sending."
        else:
            message = f"{count} welcome emails have been queued for sending."

        self.message_user(request, message, messages.SUCCESS)

    send_welcome_emails.short_description = "Send welcome emails"

    send_welcome_emails.short_description = "Send welcome emails"

    # Override get_queryset to optimize database queries
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related("profile", "created_by", "updated_by")
        )

    # Custom view methods
    def save_model(self, request, obj, form, change):
        """Override save to add audit information."""
        if not change:  # Creating new user
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile model.
    Provides detailed profile management capabilities.
    """

    list_display = (
        "user",
        "user_email",
        "user_type",
        "newsletter_subscription",
        "marketing_emails",
        "updated_at",
    )

    list_filter = (
        "newsletter_subscription",
        "marketing_emails",
        "updated_at",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "bio",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("User Information", {"fields": ("user",)}),
        ("Personal Details", {"fields": ("date_of_birth", "bio")}),
        ("Preferences", {"fields": ("newsletter_subscription", "marketing_emails")}),
        ("Social Links", {"fields": ("website",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    # Custom display methods
    def user_email(self, obj):
        """Display user's email address."""
        return obj.user.email

    user_email.short_description = "Email"
    user_email.admin_order_field = "user__email"

    def user_type(self, obj):
        """Display user's type."""
        return obj.user.get_user_type_display()

    user_type.short_description = "User Type"
    user_type.admin_order_field = "user__user_type"

    # Optimize queryset
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("user")


# Customize admin site headers
admin.site.site_header = "E-Commerce Administration"
admin.site.site_title = "E-Commerce Admin"
admin.site.index_title = "Welcome to E-Commerce Administration"
