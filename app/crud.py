"""CRUD operations for Document model."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.schemas import DocumentStatus


class DocumentCRUD:
    """CRUD operations for Document model."""

    @staticmethod
    async def create_document(
        db: AsyncSession,
        name: str,
        url: str,
        status: DocumentStatus = DocumentStatus.PENDING,
    ) -> Document:
        """Create a new document."""
        document = Document(
            name=name,
            url=url,
            status=status,
            data_progress=0.0,
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return document

    @staticmethod
    async def get_document_by_id(db: AsyncSession, document_id: str) -> Document | None:
        """Get document by UUID."""
        result = await db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_document_by_name(db: AsyncSession, name: str) -> Document | None:
        """Get document by name."""
        result = await db.execute(select(Document).where(Document.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_document_by_url(db: AsyncSession, url: str) -> Document | None:
        """Get document by URL."""
        result = await db.execute(select(Document).where(Document.url == url))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_document_by_name_and_url(
        db: AsyncSession, name: str, url: str
    ) -> Document | None:
        """Get document by exact name and URL match."""
        result = await db.execute(
            select(Document).where(Document.name == name, Document.url == url)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_conflicting_documents(
        db: AsyncSession, name: str, url: str
    ) -> tuple[Document | None, Document | None]:
        """
        Find conflicting documents for name and URL.
        Returns (name_conflict_doc, url_conflict_doc).
        If the same document matches both, it will be returned in both positions.
        """
        # Check for name conflict
        name_result = await db.execute(select(Document).where(Document.name == name))
        name_conflict = name_result.scalar_one_or_none()

        # Check for URL conflict
        url_result = await db.execute(select(Document).where(Document.url == url))
        url_conflict = url_result.scalar_one_or_none()

        return name_conflict, url_conflict

    @staticmethod
    async def reset_document_for_resummary(
        db: AsyncSession, document_id: str
    ) -> Document | None:
        """
        Reset document for re-summarization: clear summary, error, reset progress, set PENDING.
        """
        result = await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                status=DocumentStatus.PENDING,
                summary=None,
                last_error=None,
                data_progress=0.0,
                processing_time=None,
                model_used=None,
            )
            .returning(Document)
        )
        document = result.scalar_one_or_none()
        if document:
            await db.commit()
            await db.refresh(document)
        return document

    @staticmethod
    async def update_document_status(
        db: AsyncSession, document_id: str, status: DocumentStatus
    ) -> Document | None:
        """Update document status."""
        result = await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(status=status)
            .returning(Document)
        )
        document = result.scalar_one_or_none()
        if document:
            await db.commit()
        return document

    @staticmethod
    async def update_document_progress(
        db: AsyncSession, document_id: str, progress: float
    ) -> Document | None:
        """Update document progress."""
        result = await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(data_progress=progress)
            .returning(Document)
        )
        document = result.scalar_one_or_none()
        if document:
            await db.commit()
        return document

    @staticmethod
    async def update_document_summary(
        db: AsyncSession, document_id: str, summary: str
    ) -> Document | None:
        """Update document summary."""
        result = await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(summary=summary)
            .returning(Document)
        )
        document = result.scalar_one_or_none()
        if document:
            await db.commit()
        return document

    @staticmethod
    async def update_document_error(
        db: AsyncSession, document_id: str, error: str
    ) -> Document | None:
        """Update document error message."""
        result = await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(last_error=error)
            .returning(Document)
        )
        document = result.scalar_one_or_none()
        if document:
            await db.commit()
        return document

    @staticmethod
    async def get_documents_by_status(
        db: AsyncSession, status: DocumentStatus, limit: int = 100
    ) -> list[Document]:
        """Get documents by status."""
        result = await db.execute(
            select(Document)
            .where(Document.status == status)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_all_documents(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        """Get all documents with pagination."""
        result = await db.execute(
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def delete_document(db: AsyncSession, document_id: str) -> bool:
        """Delete document by UUID."""
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if document:
            await db.delete(document)
            await db.commit()
            return True
        return False


# Convenience functions
async def create_document(
    db: AsyncSession,
    name: str,
    url: str,
    status: DocumentStatus = DocumentStatus.PENDING,
) -> Document:
    """Create a new document."""
    return await DocumentCRUD.create_document(db, name, url, status)


async def get_document_by_id(db: AsyncSession, document_id: str) -> Document | None:
    """Get document by UUID."""
    return await DocumentCRUD.get_document_by_id(db, document_id)


async def update_document_status(
    db: AsyncSession, document_id: str, status: DocumentStatus
) -> Document | None:
    """Update document status."""
    return await DocumentCRUD.update_document_status(db, document_id, status)


async def update_document_progress(
    db: AsyncSession, document_id: str, progress: float
) -> Document | None:
    """Update document progress."""
    return await DocumentCRUD.update_document_progress(db, document_id, progress)


async def update_document_summary(
    db: AsyncSession, document_id: str, summary: str
) -> Document | None:
    """Update document summary."""
    return await DocumentCRUD.update_document_summary(db, document_id, summary)


async def update_document_error(
    db: AsyncSession, document_id: str, error: str
) -> Document | None:
    """Update document error message."""
    return await DocumentCRUD.update_document_error(db, document_id, error)
