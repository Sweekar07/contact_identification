from app.models import Contact, LinkPrecedence
from app.schemas import IdentifyRequest, IdentifyResponse, ContactResponse, ListUserData
from typing import List, Optional, Tuple
from tortoise.transactions import in_transaction

class ContactService:
    
    @staticmethod
    async def identify_contact(request: IdentifyRequest) -> IdentifyResponse:
        async with in_transaction():
            # Find existing contacts
            existing_contacts = await ContactService._find_existing_contacts(
                request.email, request.phone_number
            )
            
            if not existing_contacts:
                # Create new primary contact
                contact = await ContactService._create_primary_contact(
                    request.email, request.phone_number
                )
                return IdentifyResponse(
                    contact=ContactResponse(
                        primaryContactId=contact.id,
                        emails=[contact.email] if contact.email else [],
                        phoneNumbers=[contact.phone_number] if contact.phone_number else [],
                        secondaryContactIds=[]
                    )
                )
            
            # Check if we need to create secondary or merge contacts
            primary_contact, all_contacts = await ContactService._process_existing_contacts(
                existing_contacts, request.email, request.phone_number
            )
            
            return await ContactService._build_response(primary_contact, all_contacts)
    
    @staticmethod
    async def _find_existing_contacts(email: Optional[str], phone_number: Optional[str]) -> List[Contact]:
        conditions = []
        if email:
            conditions.append(Contact.filter(email=email))
        if phone_number:
            conditions.append(Contact.filter(phone_number=phone_number))
        
        if not conditions:
            return []
        
        contacts = []
        for condition in conditions:
            contacts.extend(await condition.filter(deleted_at__isnull=True))
        
        # Remove duplicates
        unique_contacts = {c.id: c for c in contacts}
        return list(unique_contacts.values())
    
    @staticmethod
    async def _create_primary_contact(email: Optional[str], phone_number: Optional[str]) -> Contact:
        return await Contact.create(
            email=email,
            phone_number=phone_number,
            linked_id=None,
            link_precedence=LinkPrecedence.primary
        )
    
    @staticmethod
    async def _process_existing_contacts(
        existing_contacts: List[Contact], 
        email: Optional[str], 
        phone_number: Optional[str]
    ) -> Tuple[Contact, List[Contact]]:
        
        # Get all related contacts (including linked ones)
        all_contact_ids = set()
        for contact in existing_contacts:
            related_ids = await ContactService._get_all_related_contact_ids(contact)
            all_contact_ids.update(related_ids)
        
        all_contacts = await Contact.filter(
            id__in=all_contact_ids, 
            deleted_at__isnull=True
        ).order_by('created_at')
        
        # Find primary contact (oldest)
        primary_contact = min(all_contacts, key=lambda x: x.created_at)
        
        # Check if we need to merge different primary contacts
        primary_contacts = [c for c in all_contacts if c.link_precedence == "primary"]
        if len(primary_contacts) > 1:
            await ContactService._merge_primary_contacts(primary_contacts)
            # Reload all contacts after merge
            all_contacts = await Contact.filter(
                id__in=all_contact_ids,
                deleted_at__isnull=True
            ).order_by('created_at')
            primary_contact = min(all_contacts, key=lambda x: x.created_at)
        
        # Check if we need to create a new secondary contact
        existing_combination = any(
            c.email == email and c.phone_number == phone_number 
            for c in all_contacts
        )
        
        if not existing_combination and (email or phone_number):
            new_contact = await Contact.create(
                email=email,
                phone_number=phone_number,
                linked_id=primary_contact.id,
                link_precedence=LinkPrecedence.secondary
            )
            all_contacts.append(new_contact)
        
        return primary_contact, all_contacts
    
    @staticmethod
    async def _get_all_related_contact_ids(contact: Contact) -> set:
        ids = {contact.id}
        
        # Find primary contact
        if contact.linked_id:
            primary = await Contact.get(id=contact.linked_id)
            ids.add(primary.id)
        else:
            primary = contact
        
        # Find all secondary contacts
        secondary_contacts = await Contact.filter(
            linked_id=primary.id,
            deleted_at__isnull=True
        )
        ids.update(c.id for c in secondary_contacts)
        
        return ids
    
    @staticmethod
    async def _merge_primary_contacts(primary_contacts: List[Contact]):
        # Keep the oldest as primary, make others secondary
        oldest = min(primary_contacts, key=lambda x: x.created_at)
        
        for contact in primary_contacts:
            if contact.id != oldest.id:
                contact.linked_id = oldest.id
                contact.link_precedence = "secondary"
                await contact.save()
                
                # Update any contacts linked to this one
                await Contact.filter(linked_id=contact.id).update(linked_id=oldest.id)
    
    @staticmethod
    async def _build_response(primary_contact: Contact, all_contacts: List[Contact]) -> IdentifyResponse:
        emails = []
        phone_numbers = []
        secondary_ids = []
        
        # Add primary contact data first
        if primary_contact.email:
            emails.append(primary_contact.email)
        if primary_contact.phone_number:
            phone_numbers.append(primary_contact.phone_number)
        
        # Add secondary contact data
        for contact in all_contacts:
            if contact.id == primary_contact.id:
                continue
                
            secondary_ids.append(contact.id)
            
            if contact.email and contact.email not in emails:
                emails.append(contact.email)
            if contact.phone_number and contact.phone_number not in phone_numbers:
                phone_numbers.append(contact.phone_number)
        
        return IdentifyResponse(
            contact=ContactResponse(
                primaryContactId=primary_contact.id,
                emails=emails,
                phoneNumbers=phone_numbers,
                secondaryContactIds=secondary_ids
            )
        )
    
    @staticmethod
    async def list_all_contacts() -> List[ListUserData]:
        contacts = await Contact.filter(deleted_at__isnull=True).order_by('created_at')
        return [ListUserData.from_contact(contact) for contact in contacts]