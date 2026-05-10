from fastapi import HTTPException, status, Depends
from typing import List
from app.models.user import User, UserRole
from app.utils.auth import get_current_user

def require_role(allowed_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        # Normalize to UserRole enum in case DB returns a plain string
        try:
            user_role = UserRole(current_user.role) if not isinstance(current_user.role, UserRole) else current_user.role
        except ValueError:
            user_role = current_user.role
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role} is not authorized to access this resource. Allowed roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker

