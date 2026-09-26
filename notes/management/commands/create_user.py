"""
Create or update a user with a password and group — without ever writing the
password into a source file.

Examples:
    python manage.py create_user rp01_admin --group Administrator --password '...'
    python manage.py create_user bob --group Junior --password '...'

If --password is omitted, you'll be prompted (input hidden).
"""
import getpass

from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from notes.models import GROUP_ADMIN


class Command(BaseCommand):
    help = "Create or update a user with a password and group."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--group", default="Administrator",
                            help="Administrator, Senior, or Junior")
        parser.add_argument("--password", default=None,
                            help="If omitted, you'll be prompted securely.")

    def handle(self, *args, **opts):
        username = opts["username"]
        group_name = opts["group"]
        password = opts["password"] or getpass.getpass("Password: ")

        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            raise CommandError(
                f"Group '{group_name}' does not exist. Run `python manage.py seed_demo` first."
            )

        user, created = User.objects.get_or_create(username=username)

        try:
            validate_password(password, user=user)
        except ValidationError as e:
            raise CommandError("Password rejected: " + "; ".join(e.messages))

        user.set_password(password)
        if group_name == GROUP_ADMIN:
            user.is_staff = True
            user.is_superuser = True
        user.save()
        user.groups.set([group])

        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} user '{username}' in group '{group_name}'."
        ))
