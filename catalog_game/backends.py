from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        email = (username or kwargs.get(UserModel.USERNAME_FIELD) or '').strip()
        if not email or password is None:
            return None
        try:
            user = UserModel._default_manager.get(email__iexact=email)
        except (UserModel.DoesNotExist, UserModel.MultipleObjectsReturned):
            UserModel().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def has_perm(self, user_obj, perm, obj=None):
        return False

    def get_all_permissions(self, user_obj, obj=None):
        return set()
