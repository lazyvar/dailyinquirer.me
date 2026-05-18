from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.confirmed_email}"


account_activation_token = AccountActivationTokenGenerator()


class EmailChangeTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.email}{user.pending_email}"


email_change_token = EmailChangeTokenGenerator()
