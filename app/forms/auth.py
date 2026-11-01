from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError

from ..security import PASSWORD_MAX_LENGTH, password_problems


def _strong_password(form, field):
    username = form.username.data if hasattr(form, "username") else ""
    email = form.email.data if hasattr(form, "email") else ""
    problems = password_problems(field.data or "", username=username or "", email=email or "")
    if problems:
        raise ValidationError(" ".join(problems))


class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Regexp(r"^[A-Za-z0-9_]{3,30}$", message="Use 3 to 30 letters, numbers or underscores."),
        ],
    )
    email = EmailField(
        "Email",
        validators=[DataRequired(), Email(check_deliverability=False), Length(max=254)],
    )
    password = PasswordField("Password", validators=[DataRequired(), _strong_password])
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="The passwords don't match.")],
    )


class LoginForm(FlaskForm):
    identifier = StringField("Username or email", validators=[DataRequired(), Length(max=254)])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(max=PASSWORD_MAX_LENGTH)]
    )


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current password", validators=[DataRequired(), Length(max=PASSWORD_MAX_LENGTH)]
    )
    password = PasswordField("New password", validators=[DataRequired(), _strong_password])
    confirm = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("password", message="The passwords don't match.")],
    )
