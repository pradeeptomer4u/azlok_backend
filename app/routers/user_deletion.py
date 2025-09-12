from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import User, AccountDeletionRequest
from ..schemas import AccountDeletionRequestCreate, AccountDeletionRequestResponse
from ..auth import get_current_user, verify_password

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.post("/delete-request", response_model=dict)
async def request_account_deletion(
    request_data: AccountDeletionRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a request to delete a user account.
    The request will be processed by administrators within 30 days.
    """
    # Verify the user's password
    if not verify_password(request_data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Create a new deletion request
    deletion_request = AccountDeletionRequest(
        user_id=current_user.id,
        reason=request_data.reason,
        status="pending",
        requested_at=datetime.utcnow()
    )
    
    db.add(deletion_request)
    db.commit()
    db.refresh(deletion_request)
    
    return {"message": "Account deletion request submitted successfully"}


@router.get("/delete-requests", response_model=List[AccountDeletionRequestResponse])
async def get_deletion_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all account deletion requests (admin only).
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )
    
    deletion_requests = db.query(AccountDeletionRequest).all()
    return deletion_requests


@router.put("/delete-requests/{request_id}/approve")
async def approve_deletion_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve an account deletion request (admin only).
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )
    
    deletion_request = db.query(AccountDeletionRequest).filter(AccountDeletionRequest.id == request_id).first()
    if not deletion_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deletion request not found"
        )
    
    # Update the request status
    deletion_request.status = "approved"
    deletion_request.processed_at = datetime.utcnow()
    deletion_request.processed_by = current_user.id
    
    # Get the user to delete
    user_to_delete = db.query(User).filter(User.id == deletion_request.user_id).first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Anonymize the user data instead of deleting
    user_to_delete.email = f"deleted_user_{user_to_delete.id}@deleted.com"
    user_to_delete.full_name = "Deleted User"
    user_to_delete.phone_number = None
    user_to_delete.is_active = False
    user_to_delete.deleted_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Account deletion request approved and user data anonymized"}


@router.put("/delete-requests/{request_id}/reject")
async def reject_deletion_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject an account deletion request (admin only).
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )
    
    deletion_request = db.query(AccountDeletionRequest).filter(AccountDeletionRequest.id == request_id).first()
    if not deletion_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deletion request not found"
        )
    
    # Update the request status
    deletion_request.status = "rejected"
    deletion_request.processed_at = datetime.utcnow()
    deletion_request.processed_by = current_user.id
    
    db.commit()
    
    return {"message": "Account deletion request rejected"}
