from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    # identifikator za prijavu — email ILI prosto korisničko ime (npr. demo "admin"/"konobar").
    # Registracija/onboarding i dalje traže pravi email (EmailStr niže) — ovde je samo login.
    email: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class RegisterIn(BaseModel):
    cafe_id: str
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    name: str = Field(min_length=1, max_length=80)
    role: str = "konobar"


class UserOut(BaseModel):
    id: str
    cafe_id: str
    email: str
    role: str
    name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class OnboardIn(BaseModel):
    """Registracija novog kafića: kreira kafić + vlasnički nalog i vraća token."""
    cafe_name: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=200)
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)
    name: str = Field(min_length=1, max_length=80)
