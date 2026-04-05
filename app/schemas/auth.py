from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=8, example="StrongPass1!")
    full_name: str = Field(..., example="John Doe")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=8, example="StrongPass1!")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., example=1800)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., example="eyJhbGci..." )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., example="CurrentPass1!")
    new_password: str = Field(..., min_length=8, example="NewPass2@")
