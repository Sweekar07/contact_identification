from enum import Enum
from tortoise.models import Model
from tortoise import fields

class LinkPrecedence(str, Enum):
    primary = "primary"
    secondary = "secondary"
    
class Contact(Model):
    id = fields.IntField(pk=True)
    phone_number = fields.CharField(max_length=20, null=True)
    email = fields.CharField(max_length=255, null=True)
    linked_id = fields.IntField(null=True)
    link_precedence = fields.CharField(LinkPrecedence)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "contacts"
