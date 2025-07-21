from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List

from app.models import Contact

class IdentifyRequest(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = Field(None, alias="phoneNumber")

class ContactResponse(BaseModel):
    primaryContactId: int = Field(..., alias="primaryContactId")
    emails: List[str]
    phoneNumbers: List[str] = Field(..., alias="phoneNumbers")
    secondaryContactIds: List[int] = Field(..., alias="secondaryContactIds")

class IdentifyResponse(BaseModel):
    contact: ContactResponse

class ListUserData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contactId: int = Field(..., alias="id")
    phoneNumber: Optional[str] = Field(None, alias="phone_number")
    email: Optional[str] = None
    linkedId: Optional[int] = Field(None, alias="linked_id")
    linkPrecedence: str = Field(..., alias="link_precedence")
    createdAt: datetime = Field(..., alias="created_at")
    updatedAt: datetime = Field(..., alias="updated_at")
    deletedAt: Optional[datetime] = Field(None, alias="deleted_at")

    @classmethod
    def from_contact(cls, contact: Contact):
        return cls.model_validate(contact)
