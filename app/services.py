from typing import List, Optional, Tuple

from app.database import get_connection
from app.models import LinkPrecedence
from app.schemas import ContactResponse, IdentifyRequest, IdentifyResponse, ListUserData


class ContactService:
    @staticmethod
    async def identify_contact(request: IdentifyRequest) -> IdentifyResponse:
        with get_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    existing_contacts = ContactService._find_existing_contacts(
                        cursor, request.email, request.phone_number
                    )

                    if not existing_contacts:
                        contact = ContactService._create_primary_contact(
                            cursor, request.email, request.phone_number
                        )
                        connection.commit()
                        return IdentifyResponse(
                            contact=ContactResponse(
                                primaryContactId=contact["id"],
                                emails=[contact["email"]] if contact["email"] else [],
                                phoneNumbers=[contact["phone_number"]]
                                if contact["phone_number"]
                                else [],
                                secondaryContactIds=[],
                            )
                        )

                    primary_contact, all_contacts = ContactService._process_existing_contacts(
                        cursor, existing_contacts, request.email, request.phone_number
                    )
                    connection.commit()
                    return ContactService._build_response(primary_contact, all_contacts)
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def _find_existing_contacts(cursor, email: Optional[str], phone_number: Optional[str]) -> List[dict]:
        filters = []
        params = []
        if email:
            filters.append("email = %s")
            params.append(email)
        if phone_number:
            filters.append("phone_number = %s")
            params.append(phone_number)

        if not filters:
            return []

        query = f"""
            SELECT *
            FROM contacts
            WHERE deleted_at IS NULL
              AND ({" OR ".join(filters)})
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()
        unique_contacts = {row["id"]: row for row in rows}
        return list(unique_contacts.values())

    @staticmethod
    def _create_primary_contact(cursor, email: Optional[str], phone_number: Optional[str]) -> dict:
        cursor.execute(
            """
            INSERT INTO contacts (email, phone_number, linked_id, link_precedence)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (email, phone_number, None, LinkPrecedence.primary.value),
        )
        return cursor.fetchone()

    @staticmethod
    def _process_existing_contacts(
        cursor, existing_contacts: List[dict], email: Optional[str], phone_number: Optional[str]
    ) -> Tuple[dict, List[dict]]:
        all_contact_ids = set()
        for contact in existing_contacts:
            related_ids = ContactService._get_all_related_contact_ids(cursor, contact)
            all_contact_ids.update(related_ids)

        all_contacts = ContactService._get_contacts_by_ids(cursor, all_contact_ids)
        primary_contact = min(all_contacts, key=lambda x: x["created_at"])

        primary_contacts = [c for c in all_contacts if c["link_precedence"] == "primary"]
        if len(primary_contacts) > 1:
            ContactService._merge_primary_contacts(cursor, primary_contacts)
            all_contacts = ContactService._get_contacts_by_ids(cursor, all_contact_ids)
            primary_contact = min(all_contacts, key=lambda x: x["created_at"])

        existing_combination = any(
            c["email"] == email and c["phone_number"] == phone_number for c in all_contacts
        )
        if not existing_combination and (email or phone_number):
            cursor.execute(
                """
                INSERT INTO contacts (email, phone_number, linked_id, link_precedence)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (email, phone_number, primary_contact["id"], LinkPrecedence.secondary.value),
            )
            all_contacts.append(cursor.fetchone())

        return primary_contact, all_contacts

    @staticmethod
    def _get_contacts_by_ids(cursor, contact_ids: set) -> List[dict]:
        if not contact_ids:
            return []
        cursor.execute(
            """
            SELECT *
            FROM contacts
            WHERE id = ANY(%s) AND deleted_at IS NULL
            ORDER BY created_at ASC
            """,
            (list(contact_ids),),
        )
        return cursor.fetchall()

    @staticmethod
    def _get_all_related_contact_ids(cursor, contact: dict) -> set:
        if contact["linked_id"]:
            primary_id = contact["linked_id"]
        else:
            primary_id = contact["id"]

        cursor.execute(
            """
            SELECT id
            FROM contacts
            WHERE deleted_at IS NULL
              AND (id = %s OR linked_id = %s)
            """,
            (primary_id, primary_id),
        )
        return {row["id"] for row in cursor.fetchall()}

    @staticmethod
    def _merge_primary_contacts(cursor, primary_contacts: List[dict]):
        oldest = min(primary_contacts, key=lambda x: x["created_at"])

        for contact in primary_contacts:
            if contact["id"] == oldest["id"]:
                continue

            cursor.execute(
                """
                UPDATE contacts
                SET linked_id = %s,
                    link_precedence = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (oldest["id"], LinkPrecedence.secondary.value, contact["id"]),
            )
            cursor.execute(
                """
                UPDATE contacts
                SET linked_id = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE linked_id = %s
                """,
                (oldest["id"], contact["id"]),
            )

    @staticmethod
    def _build_response(primary_contact: dict, all_contacts: List[dict]) -> IdentifyResponse:
        emails = []
        phone_numbers = []
        secondary_ids = []

        if primary_contact["email"]:
            emails.append(primary_contact["email"])
        if primary_contact["phone_number"]:
            phone_numbers.append(primary_contact["phone_number"])

        for contact in all_contacts:
            if contact["id"] == primary_contact["id"]:
                continue
            secondary_ids.append(contact["id"])
            if contact["email"] and contact["email"] not in emails:
                emails.append(contact["email"])
            if contact["phone_number"] and contact["phone_number"] not in phone_numbers:
                phone_numbers.append(contact["phone_number"])

        return IdentifyResponse(
            contact=ContactResponse(
                primaryContactId=primary_contact["id"],
                emails=emails,
                phoneNumbers=phone_numbers,
                secondaryContactIds=secondary_ids,
            )
        )

    @staticmethod
    async def list_all_contacts() -> List[ListUserData]:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM contacts
                    WHERE deleted_at IS NULL
                    ORDER BY created_at ASC
                    """
                )
                contacts = cursor.fetchall()
        return [ListUserData.from_contact(contact) for contact in contacts]
